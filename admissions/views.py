import csv
import io
import logging
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, TemplateView
from django.views.generic import ListView
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import EmailMultiAlternatives
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.cache import cache
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction, IntegrityError
from django.db.models import Q
from .models import MembershipApplication
from .forms import MembershipApplicationForm

logger = logging.getLogger(__name__)

User = get_user_model()


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to restrict views to full administrators only."""
    login_url = '/acceso/'

    def test_func(self):
        user = self.request.user
        return user.is_superuser or (user.is_staff and user.is_admin)

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            if self.request.user.is_staff:
                messages.warning(self.request, 'No tienes permisos para acceder a esa sección.')
                return redirect('/portal/')
            return redirect('/mi-portal/')
        return super().handle_no_permission()


def admin_required(view_func):
    """Decorator to restrict function views to admin users only."""
    def check_admin(user):
        return user.is_superuser or (user.is_staff and user.is_admin)
    return user_passes_test(check_admin, login_url='/acceso/')(view_func)


def send_application_email(application):
    """Envía email de confirmación con template HTML"""
    subject = '¡Recibimos tu solicitud! - Asociación Nuclear Colombiana'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = application.email

    # Contexto para el template
    context = {
        'first_name': application.first_name,
        'last_name': application.last_name,
        'email': application.email,
        'uuid': application.uuid,
    }

    # Renderizar templates
    html_content = render_to_string('admissions/emails/application_received.html', context)
    text_content = f"""
Hola {application.first_name},

Gracias por tu interés en formar parte de la Asociación Nuclear Colombiana.
Hemos recibido tu solicitud de membresía.

Tu código de seguimiento es: {application.uuid}

¿Qué sigue ahora?
1. Nuestro Comité de Admisiones revisará tu perfil profesional.
2. Recibirás una notificación con el resultado de la evaluación.
3. Si eres aprobado, te daremos la bienvenida oficial a la ASNC.

Si tienes alguna pregunta, no dudes en contactarnos.

Saludos,
Asociación Nuclear Colombiana
    """

    # Crear email con alternativas (texto plano + HTML)
    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def _generate_unique_username(email):
    """Generate a unique username from email address."""
    base_username = email.split('@')[0]
    username = base_username
    counter = 1

    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    return username


def create_user_from_application(application):
    """
    Creates a user account from an approved application.
    Returns the created user (existing or new).
    Uses atomic transaction to prevent race conditions.
    """
    try:
        with transaction.atomic():
            # Try to get existing user first
            user = User.objects.filter(email=application.email).first()
            if user:
                return user

            # Create username from email
            username = _generate_unique_username(application.email)

            # Create user with unusable password (will be set via email)
            user = User.objects.create_user(
                username=username,
                email=application.email,
                first_name=application.first_name,
                last_name=application.last_name,
                password=None,
            )
            user.set_unusable_password()
            user.save()

            return user

    except IntegrityError:
        # Race condition: another request created the user between our check and create
        # This is safe - just return the existing user
        logger.warning(f"Race condition detected for email {application.email}, fetching existing user")
        return User.objects.get(email=application.email)


def send_approval_email(application, user):
    """Sends approval/welcome email to the new member with password setup link."""
    subject = '¡Bienvenido a la ASNC! - Tu solicitud ha sido aprobada'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = application.email

    # Generate password reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Build password reset URL using SITE_URL from settings
    domain = settings.SITE_URL.rstrip('/')
    password_url = f"{domain}{reverse('password_set', kwargs={'uidb64': uid, 'token': token})}"

    context = {
        'first_name': application.first_name,
        'last_name': application.last_name,
        'email': application.email,
        'password_url': password_url,
    }

    html_content = render_to_string('admissions/emails/application_approved.html', context)
    text_content = f"""
Hola {application.first_name},

¡Felicidades! Tu solicitud de membresía ha sido APROBADA por el Comité de Admisiones
de la Asociación Nuclear Colombiana.

Ahora eres oficialmente parte de nuestra comunidad de profesionales comprometidos
con el desarrollo pacífico de la ciencia y tecnología nuclear en Colombia.

Para comenzar, configura tu contraseña haciendo clic en el siguiente enlace:
{password_url}

Este enlace expirará en 3 días por seguridad.

Una vez configures tu contraseña, podrás acceder al portal con tu correo {application.email}.

¡Bienvenido(a) a la ASNC!

Atentamente,
Junta Directiva
Asociación Nuclear Colombiana
    """

    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_set_password_email(user):
    """Sends email with link to set password for the first time."""
    subject = 'Configura tu contraseña - Portal ASNC'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = user.email

    # Generate password reset token
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    # Build password reset URL using SITE_URL from settings
    domain = settings.SITE_URL.rstrip('/')
    reset_url = f"{domain}{reverse('password_set', kwargs={'uidb64': uid, 'token': token})}"

    context = {
        'user': user,
        'reset_url': reset_url,
        'first_name': user.first_name,
    }

    html_content = render_to_string('admissions/emails/set_password.html', context)
    text_content = f"""
Hola {user.first_name},

Tu cuenta en el Portal de Asociados de la ASNC ha sido creada.
Para acceder, primero debes configurar tu contraseña.

Haz clic en el siguiente enlace para crear tu contraseña:
{reset_url}

Este enlace expirará en 3 días por seguridad.

Si no solicitaste esta cuenta, puedes ignorar este mensaje.

Saludos,
Asociación Nuclear Colombiana
    """

    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


def send_rejection_email(application):
    """Sends rejection email to the applicant."""
    subject = 'Resultado de tu solicitud - Asociación Nuclear Colombiana'
    from_email = settings.DEFAULT_FROM_EMAIL
    to_email = application.email

    context = {
        'first_name': application.first_name,
        'last_name': application.last_name,
    }

    html_content = render_to_string('admissions/emails/application_rejected.html', context)
    text_content = f"""
Hola {application.first_name},

Gracias por tu interés en formar parte de la Asociación Nuclear Colombiana.

Después de una cuidadosa evaluación, lamentamos informarte que en esta ocasión
tu solicitud no ha sido aprobada por el Comité de Admisiones.

Esta decisión no es definitiva. Te invitamos a volver a postularte en el futuro
cuando consideres que tu perfil se ajuste mejor a los objetivos de la asociación.

Si tienes preguntas sobre esta decisión, puedes escribirnos a info@asncol.com

Atentamente,
Comité de Admisiones
Asociación Nuclear Colombiana
    """

    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)


class ApplicationCreateView(CreateView):
    model = MembershipApplication
    form_class = MembershipApplicationForm
    template_name = 'admissions/application_form.html'
    success_url = reverse_lazy('application_success')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        signer = TimestampSigner()
        context['form_token'] = signer.sign('form')
        return context

    def form_valid(self, form):
        # Capa 2: Timestamp validation (minimum 3 seconds to fill form)
        token = form.cleaned_data.get('form_token', '')
        if token:
            try:
                signer = TimestampSigner()
                signer.unsign(token, max_age=86400)  # Valid for 24 hours
            except (BadSignature, SignatureExpired):
                # Invalid or expired token - likely a bot
                form.add_error(None, 'La sesión del formulario ha expirado. Por favor recarga la página.')
                return self.form_invalid(form)
            # Check minimum time using the signer's timestamp
            try:
                signer.unsign(token, max_age=3)
                # If this succeeds, the form was submitted in < 3 seconds
                form.add_error(None, 'Por favor toma un momento para completar el formulario.')
                return self.form_invalid(form)
            except SignatureExpired:
                # Good - form took more than 3 seconds (expected for humans)
                pass
            except BadSignature:
                form.add_error(None, 'Error en el formulario. Por favor recarga la página.')
                return self.form_invalid(form)
        else:
            # No token at all - suspicious
            form.add_error(None, 'Error en el formulario. Por favor recarga la página.')
            return self.form_invalid(form)

        # Capa 4: Rate limiting by IP (3 submissions per hour)
        ip = self._get_client_ip()
        cache_key = f'admission_rate_{ip}'
        submissions = cache.get(cache_key, 0)
        if submissions >= 3:
            form.add_error(None, 'Has enviado demasiadas solicitudes. Intenta más tarde.')
            return self.form_invalid(form)

        # Save and increment rate limit counter
        self.object = form.save()
        cache.set(cache_key, submissions + 1, 3600)  # 1 hour TTL

        # Enviamos el correo HTML
        try:
            send_application_email(self.object)
        except Exception:
            # Si falla el email, no interrumpimos el flujo
            pass

        return super().form_valid(form)

    def _get_client_ip(self):
        """Extract client IP from request, handling proxies."""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR', '')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR', '')


class ApplicationSuccessView(TemplateView):
    template_name = 'admissions/application_success.html'


class ApplicationListView(AdminRequiredMixin, LoginRequiredMixin, ListView):
    model = MembershipApplication
    template_name = 'dashboard/application_list.html'
    context_object_name = 'applications'
    ordering = ['-created_at']
    paginate_by = 15

    def get_queryset(self):
        queryset = super().get_queryset()

        # Search by name, email, profession or institution
        search = self.request.GET.get('q', '').strip()
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(profession__icontains=search) |
                Q(institution__icontains=search)
            )

        # Filter by status
        status = self.request.GET.get('status')
        if status in MembershipApplication.Status.values:
            queryset = queryset.filter(status=status)

        # Filter by sector
        sector = self.request.GET.get('sector')
        if sector in MembershipApplication.Sector.values:
            queryset = queryset.filter(sector=sector)

        # Filter by contact flag
        contactado = self.request.GET.get('contactado')
        if contactado in ('1', '0'):
            queryset = queryset.filter(contactado=(contactado == '1'))

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Current filter state (used to repopulate the form and paginator links)
        context['search_query'] = self.request.GET.get('q', '').strip()
        context['status_choices'] = MembershipApplication.Status.choices
        context['sector_choices'] = MembershipApplication.Sector.choices
        context['current_status'] = self.request.GET.get('status', '')
        context['current_sector'] = self.request.GET.get('sector', '')
        context['current_contactado'] = self.request.GET.get('contactado', '')
        context['has_filters'] = any([
            context['search_query'], context['current_status'],
            context['current_sector'], context['current_contactado'],
        ])

        # Querystring with the active filters, so pagination keeps them
        params = self.request.GET.copy()
        params.pop('page', None)
        context['filter_querystring'] = params.urlencode()

        # Build a dictionary of password status for completed applications
        password_status = {}
        for app in context['applications']:
            if app.status == MembershipApplication.Status.COMPLETED:
                user = User.objects.filter(email=app.email).first()
                if user:
                    password_status[app.pk] = {
                        'user_exists': True,
                        'has_password': user.has_usable_password(),
                        'last_login': user.last_login,
                    }
                else:
                    password_status[app.pk] = {'user_exists': False}
        context['password_status'] = password_status
        return context


class ApplicationDetailView(AdminRequiredMixin, LoginRequiredMixin, DetailView):
    model = MembershipApplication
    template_name = 'dashboard/application_detail.html'
    context_object_name = 'app'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        app = self.object
        # Get user info for completed applications
        if app.status == MembershipApplication.Status.COMPLETED:
            user = User.objects.filter(email=app.email).first()
            if user:
                context['linked_user'] = user
                context['has_password'] = user.has_usable_password()
                context['last_login'] = user.last_login
        return context


@login_required
@admin_required
def change_application_status(request, pk, status):
    """
    Handle application status changes (approve/reject).
    Uses atomic transaction to ensure data consistency.
    """
    application = get_object_or_404(MembershipApplication, pk=pk)

    if status == 'approved':
        user = None
        try:
            # Use atomic transaction to ensure user + status update are consistent
            with transaction.atomic():
                # Lock the application row to prevent concurrent updates
                application = MembershipApplication.objects.select_for_update().get(pk=pk)

                # Verify status hasn't changed (idempotency check)
                if application.status == MembershipApplication.Status.COMPLETED:
                    messages.info(request, f'{application.first_name} ya fue vinculado anteriormente.')
                    return redirect('application_detail', pk=pk)

                # 1. Create user account
                user = create_user_from_application(application)

                # 2. Update application status to COMPLETED
                application.status = MembershipApplication.Status.COMPLETED
                application.save()

            # 3. Send welcome email OUTSIDE transaction (email can fail without rollback)
            try:
                send_approval_email(application, user)
                messages.success(
                    request,
                    f'¡{application.first_name} {application.last_name} ha sido APROBADO y VINCULADO! '
                    f'Se ha enviado el correo de bienvenida con el enlace para configurar contraseña.'
                )
            except Exception as e:
                logger.error(f'Failed to send approval email to {application.email}: {e}')
                messages.warning(
                    request,
                    'Usuario creado exitosamente, pero falló el envío del correo de bienvenida. '
                    'Puede reenviar el correo desde el detalle de la solicitud.'
                )

        except Exception as e:
            logger.error(f'Error processing approval for application {pk}: {e}')
            messages.error(request, 'Error al procesar la aprobación. Por favor intente de nuevo.')

    elif status == 'rejected':
        try:
            with transaction.atomic():
                application = MembershipApplication.objects.select_for_update().get(pk=pk)
                application.status = MembershipApplication.Status.REJECTED
                application.save()

            # Send rejection email outside transaction
            try:
                send_rejection_email(application)
            except Exception as e:
                logger.error(f'Failed to send rejection email to {application.email}: {e}')
                messages.warning(
                    request,
                    'Solicitud rechazada, pero falló el envío del correo de notificación.'
                )

            messages.warning(request, f'La solicitud de {application.first_name} ha sido rechazada.')

        except Exception as e:
            logger.error(f'Error rejecting application {pk}: {e}')
            messages.error(request, 'Error al rechazar la solicitud. Por favor intente de nuevo.')

    return redirect('application_detail', pk=pk)


# ============================================================================
# Exportación de solicitudes (CSV / Excel)
# ============================================================================

EXPORT_HEADERS = [
    'Nombres', 'Apellidos', 'Correo', 'Teléfono', 'Profesión',
    'Cargo actual', 'Institución', 'LinkedIn', 'Sector', 'Estado',
    'Contactado', 'Notas internas', 'Aporte a la ASNC', 'Fecha de registro',
]

# Índices de columnas con formato especial (0-based)
_COL_SECTOR = 8
_COL_STATUS = 9
_COL_CONTACTADO = 10


def _get_applications_for_export():
    return MembershipApplication.objects.all().order_by('-created_at')


def _application_row_values(app):
    """Fila de valores en el mismo orden que EXPORT_HEADERS."""
    return [
        app.first_name,
        app.last_name,
        app.email,
        app.phone,
        app.profession,
        app.current_job,
        app.institution,
        app.linkedin_url,
        app.get_sector_display() if app.sector else '',
        app.get_status_display(),
        'Sí' if app.contactado else 'No',
        app.admin_notes,
        app.contribution_statement,
        timezone.localtime(app.created_at).strftime('%d/%m/%Y %H:%M'),
    ]


@login_required
@admin_required
def export_applications_csv(request):
    """Exporta todas las solicitudes a CSV (compatible con Excel, BOM UTF-8)."""
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="solicitudes_asnc.csv"'
    response.write('﻿')  # BOM para que Excel reconozca acentos

    writer = csv.writer(response)
    writer.writerow(EXPORT_HEADERS)
    for app in _get_applications_for_export():
        writer.writerow(_application_row_values(app))
    return response


@login_required
@admin_required
def export_applications_excel(request):
    """Exporta todas las solicitudes a un .xlsx con encabezados y estados a color."""
    import xlsxwriter

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    ws = workbook.add_worksheet('Solicitudes')

    # --- Formatos ---
    header_fmt = workbook.add_format({
        'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#1B2A41',
        'border': 1, 'border_color': '#0F1A2B',
        'align': 'center', 'valign': 'vcenter', 'text_wrap': True,
    })
    base = {'border': 1, 'border_color': '#E2E8F0', 'valign': 'top', 'text_wrap': True}
    cell_fmt = workbook.add_format(base)

    def colored(bg, fg):
        f = dict(base)
        f.update({'bg_color': bg, 'font_color': fg, 'align': 'center', 'bold': True})
        return workbook.add_format(f)

    status_fmts = {
        MembershipApplication.Status.PENDING: colored('#FFF3CD', '#856404'),
        MembershipApplication.Status.UNDER_REVIEW: colored('#CFE2FF', '#084298'),
        MembershipApplication.Status.APPROVED: colored('#D1E7DD', '#0F5132'),
        MembershipApplication.Status.REJECTED: colored('#F8D7DA', '#842029'),
        MembershipApplication.Status.COMPLETED: colored('#E2E3E5', '#41464B'),
    }
    sector_fmt = colored('#CFF4FC', '#055160')
    contactado_si = colored('#D1E7DD', '#0F5132')
    contactado_no = colored('#F1F3F5', '#6C757D')

    # --- Anchos de columna ---
    widths = [16, 16, 28, 16, 22, 22, 22, 28, 22, 18, 12, 32, 45, 18]
    for i, w in enumerate(widths):
        ws.set_column(i, i, w)

    # --- Encabezado ---
    ws.set_row(0, 28)
    ws.write_row(0, 0, EXPORT_HEADERS, header_fmt)
    ws.freeze_panes(1, 0)
    ws.autofilter(0, 0, 0, len(EXPORT_HEADERS) - 1)

    # --- Datos ---
    row_idx = 1
    for app in _get_applications_for_export():
        values = _application_row_values(app)
        for col, value in enumerate(values):
            if col == _COL_STATUS:
                fmt = status_fmts.get(app.status, cell_fmt)
            elif col == _COL_CONTACTADO:
                fmt = contactado_si if app.contactado else contactado_no
            elif col == _COL_SECTOR and app.sector:
                fmt = sector_fmt
            else:
                fmt = cell_fmt
            ws.write(row_idx, col, value, fmt)
        row_idx += 1

    workbook.close()
    output.seek(0)

    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="solicitudes_asnc.xlsx"'
    return response


@login_required
@admin_required
def update_application_admin(request, pk):
    """Update internal committee fields: 'contactado' flag and notes."""
    application = get_object_or_404(MembershipApplication, pk=pk)

    if request.method == 'POST':
        application.contactado = request.POST.get('contactado') == 'true'
        application.admin_notes = request.POST.get('admin_notes', '').strip()

        sector = request.POST.get('sector', '')
        valid_sectors = {choice[0] for choice in MembershipApplication.Sector.choices}
        application.sector = sector if sector in valid_sectors else ''

        application.save()
        messages.success(request, 'Información interna actualizada correctamente.')

    return redirect('application_detail', pk=pk)


@login_required
@admin_required
def resend_password_email(request, pk):
    """Resend the password setup email to a user."""
    application = get_object_or_404(MembershipApplication, pk=pk)

    # Only for completed applications
    if application.status != MembershipApplication.Status.COMPLETED:
        messages.error(request, 'Solo se puede reenviar el correo a usuarios vinculados.')
        return redirect('application_detail', pk=pk)

    # Find the user
    user = User.objects.filter(email=application.email).first()
    if not user:
        messages.error(request, 'No se encontró un usuario asociado a esta solicitud.')
        return redirect('application_detail', pk=pk)

    # Check if user already has a password
    if user.has_usable_password():
        messages.warning(request, f'{user.first_name} ya configuró su contraseña.')
        return redirect('application_detail', pk=pk)

    # Send the password setup email
    try:
        send_set_password_email(user)
        messages.success(
            request,
            f'Se ha reenviado el correo de configuración de contraseña a {user.email}.'
        )
    except Exception as e:
        messages.error(request, 'Error al enviar el correo. Por favor intente de nuevo.')

    return redirect('application_detail', pk=pk)
