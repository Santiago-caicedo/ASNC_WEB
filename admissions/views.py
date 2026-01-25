from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.views.generic import ListView
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import MembershipApplication
from .forms import MembershipApplicationForm


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


class ApplicationListView(LoginRequiredMixin, ListView):
    model = MembershipApplication
    template_name = 'dashboard/application_list.html' # Ojo a la ruta
    context_object_name = 'applications'
    ordering = ['-created_at']



# 1. VISTA DE DETALLE (El Expediente)
class ApplicationDetailView(LoginRequiredMixin, DetailView):
    model = MembershipApplication
    template_name = 'dashboard/application_detail.html' # Ojo: usaremos la carpeta dashboard
    context_object_name = 'app'

# 2. VISTA DE ACCIÓN (Para los botones)
@login_required
def change_application_status(request, pk, status):
    application = get_object_or_404(MembershipApplication, pk=pk)
    
    if status == 'approved':
        application.status = 'APPROVED'
        application.save()
        messages.success(request, f'El candidato {application.first_name} ha sido APROBADO exitosamente.')
        # AQUÍ IRÍA LA LÓGICA DE CREAR USUARIO AUTOMÁTICO (Lo haremos en la siguiente fase)
        
        # Enviar correo (Opcional por ahora)
        # send_mail(...) 

    elif status == 'rejected':
        application.status = 'REJECTED'
        application.save()
        messages.warning(request, f'La solicitud de {application.first_name} ha sido rechazada.')
    
    return redirect('application_detail', pk=pk)