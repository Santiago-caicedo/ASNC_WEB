import logging
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.generic import TemplateView, ListView, DetailView, FormView, View
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.db.models import Count, Q
from django.db import transaction

from .models import MemberCard, CardVerification

logger = logging.getLogger(__name__)

# Token expiration time in hours
PHOTO_TOKEN_EXPIRY_HOURS = 72  # 3 days


class StaffRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict views to staff/superuser only."""
    login_url = '/acceso/'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            return redirect('/mi-portal/')
        return super().handle_no_permission()


def staff_required(view_func):
    """Decorator to restrict function views to staff/superuser only."""
    def check_staff(user):
        return user.is_staff or user.is_superuser
    return user_passes_test(check_staff, login_url='/acceso/')(view_func)
from .forms import PhotoUploadForm, GenerateCardForm, CardSuspendForm, CardRenewForm
from .utils import (
    generate_card_pdf,
    send_photo_request_email,
    send_card_ready_email
)
from admissions.models import MembershipApplication


# ============================================
# Public Views (No login required)
# ============================================

class CardVerificationView(TemplateView):
    """Public page for verifying a member card via QR code."""
    template_name = 'carnets/verificar.html'

    def get(self, request, uuid):
        try:
            card = MemberCard.objects.select_related('user', 'application').get(uuid=uuid)
        except MemberCard.DoesNotExist:
            return render(request, 'carnets/verificar.html', {
                'valid': False,
                'error': 'Carné no encontrado'
            })

        # Log the verification
        CardVerification.objects.create(
            card=card,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
        )

        # Check validity
        is_valid = card.is_valid

        context = {
            'card': card,
            'valid': is_valid,
            'verification_count': card.verifications.count(),
        }

        return render(request, self.template_name, context)

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PhotoUploadView(FormView):
    """Public page for associates to upload their photo via secure token."""
    template_name = 'carnets/subir_foto.html'
    form_class = PhotoUploadForm

    def dispatch(self, request, *args, **kwargs):
        # Get the card by token
        token = kwargs.get('token')
        try:
            self.card = MemberCard.objects.get(photo_token=token)
        except MemberCard.DoesNotExist:
            raise Http404("Enlace inválido o expirado")

        # Check if token was already used
        if self.card.photo_token_used:
            return render(request, 'carnets/subir_foto.html', {
                'token_used': True,
                'card': self.card
            })

        # Check if token has expired (72 hours / 3 days)
        if self.card.photo_token_created_at:
            expiry_time = self.card.photo_token_created_at + timedelta(hours=PHOTO_TOKEN_EXPIRY_HOURS)
            if timezone.now() > expiry_time:
                return render(request, 'carnets/subir_foto.html', {
                    'token_expired': True,
                    'card': self.card
                })

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['card'] = self.card
        return context

    def form_valid(self, form):
        """
        Save the photo using atomic transaction with row locking
        to prevent race conditions from concurrent uploads.
        """
        try:
            with transaction.atomic():
                # Lock the card row to prevent concurrent updates
                card = MemberCard.objects.select_for_update().get(pk=self.card.pk)

                # Double-check token hasn't been used (race condition guard)
                if card.photo_token_used:
                    return render(self.request, 'carnets/subir_foto.html', {
                        'token_used': True,
                        'card': card
                    })

                # Save the photo and update status atomically
                card.photo = form.cleaned_data['photo']
                card.photo_token_used = True
                card.status = MemberCard.Status.ACTIVE
                card.save()

            # Send notification email OUTSIDE transaction
            try:
                send_card_ready_email(card)
            except Exception as e:
                logger.error(f'Failed to send card ready email to {card.user.email}: {e}')
                # Don't break the flow if email fails - card is still activated

            return redirect('carnets:subir_foto_exito', token=card.photo_token)

        except Exception as e:
            logger.error(f'Error uploading photo for card {self.card.card_number}: {e}')
            messages.error(self.request, 'Error al procesar la foto. Por favor intente de nuevo.')
            return self.form_invalid(form)


class PhotoUploadSuccessView(TemplateView):
    """Success page after photo upload."""
    template_name = 'carnets/subir_foto_exito.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.kwargs.get('token')
        try:
            context['card'] = MemberCard.objects.get(photo_token=token)
        except MemberCard.DoesNotExist:
            pass
        return context


# ============================================
# Associate Views (Login required)
# ============================================

class MyCardView(LoginRequiredMixin, TemplateView):
    """View for associates to see their own card."""
    template_name = 'carnets/mi_carne.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['card'] = MemberCard.objects.get(user=self.request.user)
        except MemberCard.DoesNotExist:
            context['card'] = None
        return context


class MyCardDownloadView(LoginRequiredMixin, View):
    """Download PDF of member's own card."""

    def get(self, request):
        try:
            card = MemberCard.objects.get(user=request.user)
        except MemberCard.DoesNotExist:
            messages.error(request, 'No tienes un carné digital asociado.')
            return redirect('carnets:mi_carne')

        if card.status != MemberCard.Status.ACTIVE:
            messages.error(request, 'Tu carné no está activo.')
            return redirect('carnets:mi_carne')

        # Generate PDF
        pdf_buffer = generate_card_pdf(card)

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="carne_asnc_{card.card_number}.pdf"'

        return response


# ============================================
# Dashboard Views (Admin - Login required)
# ============================================

class CardListView(StaffRequiredMixin, LoginRequiredMixin, ListView):
    """List all member cards in dashboard."""
    model = MemberCard
    template_name = 'carnets/dashboard/list.html'
    context_object_name = 'cards'
    ordering = ['-created_at']
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user', 'issued_by')

        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        # Search by name or card number
        search = self.request.GET.get('q')
        if search:
            queryset = queryset.filter(
                Q(card_number__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = MemberCard.Status.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['search_query'] = self.request.GET.get('q', '')
        return context


class CardDetailView(StaffRequiredMixin, LoginRequiredMixin, DetailView):
    """Detail view of a member card in dashboard."""
    model = MemberCard
    template_name = 'carnets/dashboard/detail.html'
    context_object_name = 'card'

    def get_queryset(self):
        return super().get_queryset().select_related('user', 'application', 'issued_by')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_verifications'] = self.object.verifications.all()[:10]
        return context


class GenerateCardView(StaffRequiredMixin, LoginRequiredMixin, FormView):
    """View to initiate card generation from an approved application."""
    template_name = 'carnets/dashboard/generar_carne.html'
    form_class = GenerateCardForm

    def dispatch(self, request, *args, **kwargs):
        self.application = get_object_or_404(MembershipApplication, pk=kwargs.get('pk'))

        # Check if application is in COMPLETED status
        if self.application.status != MembershipApplication.Status.COMPLETED:
            messages.error(request, 'Solo se pueden generar carnés para solicitudes con estado "Vinculado".')
            return redirect('application_detail', pk=self.application.pk)

        # Check if card already exists
        if hasattr(self.application, 'member_card'):
            messages.warning(request, 'Ya existe un carné para esta solicitud.')
            return redirect('carnets:card_detail', pk=self.application.member_card.pk)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['application'] = self.application
        return context

    def form_valid(self, form):
        from django.contrib.auth import get_user_model
        from django.db import IntegrityError
        User = get_user_model()

        # Try to find the user associated with this application
        try:
            user = User.objects.get(email=self.application.email)
        except User.DoesNotExist:
            messages.error(
                self.request,
                'No existe un usuario con el correo de esta solicitud. '
                'Primero debe crearse el usuario del asociado.'
            )
            return redirect('application_detail', pk=self.application.pk)

        try:
            # Use atomic transaction to ensure card number uniqueness
            with transaction.atomic():
                # Generate card number (already uses select_for_update internally)
                card_number = MemberCard.generate_card_number()

                # Create the card
                card = MemberCard.objects.create(
                    card_number=card_number,
                    user=user,
                    application=self.application,
                    category=form.cleaned_data['category'],
                    issued_by=self.request.user,
                    status=MemberCard.Status.PENDING_PHOTO,
                    photo_token_created_at=timezone.now()  # Track token creation time
                )

        except IntegrityError as e:
            logger.error(f'IntegrityError creating card for {user.email}: {e}')
            # Check if it's a duplicate card number (race condition) or duplicate user
            if 'card_number' in str(e):
                messages.error(self.request, 'Error de concurrencia al generar el número de carné. Por favor intente de nuevo.')
            elif 'user' in str(e):
                messages.error(self.request, 'Este usuario ya tiene un carné asignado.')
            else:
                messages.error(self.request, 'Error al crear el carné. Por favor intente de nuevo.')
            return redirect('application_detail', pk=self.application.pk)

        # Send photo request email OUTSIDE transaction
        if form.cleaned_data.get('send_email', True):
            try:
                send_photo_request_email(card)
                messages.success(
                    self.request,
                    f'Carné {card_number} generado exitosamente. '
                    f'Se ha enviado un correo a {user.email} solicitando la foto.'
                )
            except Exception as e:
                logger.error(f'Failed to send photo request email to {user.email}: {e}')
                messages.warning(
                    self.request,
                    f'Carné {card_number} generado, pero hubo un error al enviar el correo.'
                )
        else:
            messages.success(self.request, f'Carné {card_number} generado exitosamente.')

        return redirect('carnets:card_detail', pk=card.pk)


class CardSuspendView(StaffRequiredMixin, LoginRequiredMixin, FormView):
    """View to suspend a member card."""
    template_name = 'carnets/dashboard/suspender.html'
    form_class = CardSuspendForm

    def dispatch(self, request, *args, **kwargs):
        self.card = get_object_or_404(MemberCard, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['card'] = self.card
        return context

    def form_valid(self, form):
        self.card.status = MemberCard.Status.SUSPENDED
        self.card.suspension_reason = form.cleaned_data['reason']
        self.card.save()

        messages.success(self.request, f'El carné {self.card.card_number} ha sido suspendido.')
        return redirect('carnets:card_detail', pk=self.card.pk)


@login_required
@staff_required
def reactivate_card(request, pk):
    """Reactivate a suspended card."""
    card = get_object_or_404(MemberCard, pk=pk)

    if card.status != MemberCard.Status.SUSPENDED:
        messages.error(request, 'Solo se pueden reactivar carnés suspendidos.')
        return redirect('carnets:card_detail', pk=pk)

    # Check if card has a photo
    if not card.photo:
        card.status = MemberCard.Status.PENDING_PHOTO
    else:
        card.status = MemberCard.Status.ACTIVE

    card.suspension_reason = ''
    card.save()

    messages.success(request, f'El carné {card.card_number} ha sido reactivado.')
    return redirect('carnets:card_detail', pk=pk)


class CardRenewView(StaffRequiredMixin, LoginRequiredMixin, FormView):
    """View to renew a member card."""
    template_name = 'carnets/dashboard/renovar.html'
    form_class = CardRenewForm

    def dispatch(self, request, *args, **kwargs):
        self.card = get_object_or_404(MemberCard, pk=kwargs.get('pk'))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['card'] = self.card
        return context

    def form_valid(self, form):
        new_year = form.cleaned_data['new_expiry_year']
        self.card.expiry_date = timezone.datetime(new_year, 12, 31).date()

        # If card was expired, reactivate it
        if self.card.status == MemberCard.Status.EXPIRED:
            if self.card.photo:
                self.card.status = MemberCard.Status.ACTIVE
            else:
                self.card.status = MemberCard.Status.PENDING_PHOTO

        self.card.save()

        messages.success(
            self.request,
            f'El carné {self.card.card_number} ha sido renovado hasta el 31/12/{new_year}.'
        )
        return redirect('carnets:card_detail', pk=self.card.pk)


class CardStatsView(StaffRequiredMixin, LoginRequiredMixin, TemplateView):
    """Dashboard statistics for member cards."""
    template_name = 'carnets/dashboard/estadisticas.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Card counts by status
        context['total_cards'] = MemberCard.objects.count()
        context['active_cards'] = MemberCard.objects.filter(status=MemberCard.Status.ACTIVE).count()
        context['pending_photo'] = MemberCard.objects.filter(status=MemberCard.Status.PENDING_PHOTO).count()
        context['expired_cards'] = MemberCard.objects.filter(status=MemberCard.Status.EXPIRED).count()
        context['suspended_cards'] = MemberCard.objects.filter(status=MemberCard.Status.SUSPENDED).count()

        # Card counts by category
        context['founder_cards'] = MemberCard.objects.filter(category=MemberCard.Category.FOUNDER).count()
        context['associate_cards'] = MemberCard.objects.filter(category=MemberCard.Category.ASSOCIATE).count()

        # Verification stats
        context['total_verifications'] = CardVerification.objects.count()
        context['verifications_today'] = CardVerification.objects.filter(
            verified_at__date=timezone.now().date()
        ).count()

        # Recent cards
        context['recent_cards'] = MemberCard.objects.select_related('user').order_by('-created_at')[:5]

        # Cards expiring soon (within 30 days)
        thirty_days = timezone.now().date() + timezone.timedelta(days=30)
        context['expiring_soon'] = MemberCard.objects.filter(
            status=MemberCard.Status.ACTIVE,
            expiry_date__lte=thirty_days
        ).count()

        return context


@login_required
@staff_required
def resend_photo_request(request, pk):
    """Resend photo request email to associate."""
    card = get_object_or_404(MemberCard, pk=pk)

    if card.status != MemberCard.Status.PENDING_PHOTO:
        messages.error(request, 'Solo se puede reenviar la solicitud para carnés pendientes de foto.')
        return redirect('carnets:card_detail', pk=pk)

    try:
        send_photo_request_email(card)
        messages.success(request, f'Se ha reenviado la solicitud de foto a {card.user.email}.')
    except Exception as e:
        messages.error(request, 'Error al enviar el correo. Por favor intente de nuevo.')

    return redirect('carnets:card_detail', pk=pk)
