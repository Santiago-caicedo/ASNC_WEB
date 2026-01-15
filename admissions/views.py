from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from django.views.generic import ListView
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
from .models import MembershipApplication
from .forms import MembershipApplicationForm

class ApplicationCreateView(CreateView):
    model = MembershipApplication
    form_class = MembershipApplicationForm
    template_name = 'admissions/application_form.html'
    success_url = reverse_lazy('application_success')

    def form_valid(self, form):
        # Primero guardamos el objeto en la BD
        self.object = form.save()
        
        # Luego enviamos el correo
        # Nota: self.object.email accede al email que el usuario acaba de escribir
        send_mail(
            subject='Recibimos tu solicitud - ASNC',
            message=f'Hola {self.object.first_name}, hemos recibido tu solicitud. Tu código de seguimiento es: {self.object.uuid}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.object.email],
            fail_silently=False,
        )
        
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