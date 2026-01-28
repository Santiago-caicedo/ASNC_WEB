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
from django.template.loader import render_to_string
from django.conf import settings
from .models import MembershipApplication
from .forms import MembershipApplicationForm

User = get_user_model()


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


def create_user_from_application(application):
    """
    Creates a user account from an approved application.
    Returns the created user or None if user already exists.
    """
    # Check if user already exists
    if User.objects.filter(email=application.email).exists():
        return User.objects.get(email=application.email)

    # Create username from email (before @)
    base_username = application.email.split('@')[0]
    username = base_username
    counter = 1

    # Ensure unique username
    while User.objects.filter(username=username).exists():
        username = f"{base_username}{counter}"
        counter += 1

    # Create user with unusable password (will be set via email)
    user = User.objects.create_user(
        username=username,
        email=application.email,
        first_name=application.first_name,
        last_name=application.last_name,
        password=None,  # No password yet
    )
    user.set_unusable_password()
    user.save()

    return user


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

    def form_valid(self, form):
        # Guardamos el objeto en la BD
        self.object = form.save()

        # Enviamos el correo HTML
        try:
            send_application_email(self.object)
        except Exception:
            # Si falla el email, no interrumpimos el flujo
            pass

        return super().form_valid(form)


class ApplicationSuccessView(TemplateView):
    template_name = 'admissions/application_success.html'


class ApplicationListView(StaffRequiredMixin, LoginRequiredMixin, ListView):
    model = MembershipApplication
    template_name = 'dashboard/application_list.html'
    context_object_name = 'applications'
    ordering = ['-created_at']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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


class ApplicationDetailView(StaffRequiredMixin, LoginRequiredMixin, DetailView):
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
@staff_required
def change_application_status(request, pk, status):
    """Handle application status changes (approve/reject)."""
    application = get_object_or_404(MembershipApplication, pk=pk)

    if status == 'approved':
        try:
            # 1. Create user account
            user = create_user_from_application(application)

            # 2. Update application status to COMPLETED
            application.status = MembershipApplication.Status.COMPLETED
            application.save()

            # 3. Send welcome email (includes password setup link)
            try:
                send_approval_email(application, user)
            except Exception as e:
                messages.warning(request, f'Usuario creado, pero falló el envío del correo de bienvenida: {e}')

            messages.success(
                request,
                f'¡{application.first_name} {application.last_name} ha sido APROBADO y VINCULADO! '
                f'Se ha enviado el correo de bienvenida con el enlace para configurar contraseña.'
            )

        except Exception as e:
            messages.error(request, f'Error al procesar la aprobación: {e}')

    elif status == 'rejected':
        application.status = MembershipApplication.Status.REJECTED
        application.save()

        # Send rejection email
        try:
            send_rejection_email(application)
        except Exception:
            pass  # Don't block if email fails

        messages.warning(request, f'La solicitud de {application.first_name} ha sido rechazada.')

    return redirect('application_detail', pk=pk)


@login_required
@staff_required
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
        messages.error(request, f'Error al enviar el correo: {e}')

    return redirect('application_detail', pk=pk)
