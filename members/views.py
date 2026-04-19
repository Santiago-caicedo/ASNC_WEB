import base64
from io import BytesIO

from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.views.generic import TemplateView, View, UpdateView
from django.http import HttpResponse
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from carnets.models import MemberCard
from carnets.utils import generate_card_pdf, generate_qr_code, get_verification_url
from .forms import ProfileEditForm


def build_qr_data_uri(card):
    """Render a MemberCard's verification QR as a base64 PNG data URI."""
    qr_img = generate_qr_code(get_verification_url(card), size=200)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def get_membership_duration(user):
    """
    Calculate the membership duration for a user.
    Returns a dict with years, months, and a formatted string.
    """
    # Try to get the card issue date first, fallback to user registration
    try:
        card = MemberCard.objects.get(user=user)
        start_date = card.issue_date
    except MemberCard.DoesNotExist:
        start_date = user.date_joined.date()

    today = timezone.now().date()
    delta = relativedelta(today, start_date)

    return {
        'years': delta.years,
        'months': delta.months,
        'days': delta.days,
        'start_date': start_date,
        'formatted': format_duration(delta.years, delta.months),
    }


def format_duration(years, months):
    """Format the duration as a readable string in Spanish."""
    parts = []
    if years > 0:
        parts.append(f"{years} {'año' if years == 1 else 'años'}")
    if months > 0:
        parts.append(f"{months} {'mes' if months == 1 else 'meses'}")
    if not parts:
        return "Menos de un mes"
    return ', '.join(parts)


class MemberLoginView(LoginView):
    """Login view for regular members (associates)."""
    template_name = 'members/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        if user.is_admin:
            return '/portal/'
        if user.is_staff and user.can_edit_news:
            return '/portal/noticias/'
        return '/mi-portal/'


class MemberDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard home for regular members."""
    template_name = 'members/dashboard.html'
    login_url = '/acceso/'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_admin:
            return redirect('/portal/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get user's card if exists
        try:
            context['card'] = MemberCard.objects.get(user=self.request.user)
        except MemberCard.DoesNotExist:
            context['card'] = None
        # Add membership duration
        context['membership'] = get_membership_duration(self.request.user)
        return context


class MemberCardView(LoginRequiredMixin, TemplateView):
    """View for members to see their digital card."""
    template_name = 'members/card.html'
    login_url = '/acceso/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            card = MemberCard.objects.get(user=self.request.user)
            context['card'] = card
            if card.status == MemberCard.Status.ACTIVE:
                context['qr_data_uri'] = build_qr_data_uri(card)
        except MemberCard.DoesNotExist:
            context['card'] = None
        return context


class MemberCardDownloadView(LoginRequiredMixin, View):
    """Download PDF of member's card."""
    login_url = '/acceso/'

    def get(self, request):
        try:
            card = MemberCard.objects.get(user=request.user)
        except MemberCard.DoesNotExist:
            messages.error(request, 'No tienes un carné digital asociado.')
            return redirect('members:dashboard')

        if card.status != MemberCard.Status.ACTIVE:
            messages.error(request, 'Tu carné no está activo.')
            return redirect('members:card')

        # Generate PDF
        pdf_buffer = generate_card_pdf(card)

        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Carne_ASNC_{card.card_number}.pdf"'

        return response


class MemberProfileView(LoginRequiredMixin, TemplateView):
    """View for members to see their profile."""
    template_name = 'members/profile.html'
    login_url = '/acceso/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        context['membership'] = get_membership_duration(self.request.user)
        return context


class MemberPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """View for members to change their password."""
    template_name = 'members/password_change.html'
    success_url = reverse_lazy('members:password_change_done')
    login_url = '/acceso/'

    def form_valid(self, form):
        messages.success(self.request, 'Tu contraseña ha sido actualizada exitosamente.')
        return super().form_valid(form)


class MemberPasswordChangeDoneView(LoginRequiredMixin, TemplateView):
    """View shown after successful password change."""
    template_name = 'members/password_change_done.html'
    login_url = '/acceso/'


class MemberProfileEditView(LoginRequiredMixin, UpdateView):
    """View for members to edit their profile information."""
    template_name = 'members/profile_edit.html'
    form_class = ProfileEditForm
    success_url = reverse_lazy('members:profile')
    login_url = '/acceso/'

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Tu perfil ha sido actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['membership'] = get_membership_duration(self.request.user)
        return context
