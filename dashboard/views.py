from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, FormView
from django.urls import reverse_lazy
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from admissions.models import MembershipApplication
from website.models import FeaturedMember
from .forms import FeaturedMemberForm, EmailComposeForm
from .models import SentEmail


# 1. Login Personalizado
class CustomLoginView(LoginView):
    template_name = 'dashboard/login.html'
    redirect_authenticated_user = True


# 2. Home del Dashboard (Resumen)
class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Traemos contadores para las tarjetas de resumen
        context['pending_count'] = MembershipApplication.objects.filter(status='PENDING').count()
        context['review_count'] = MembershipApplication.objects.filter(status='REVIEW').count()
        context['members_count'] = FeaturedMember.objects.filter(is_active=True).count()
        return context


# ============================================
# CRUD para Asociados Destacados
# ============================================

class FeaturedMemberListView(LoginRequiredMixin, ListView):
    """Lista de asociados destacados"""
    model = FeaturedMember
    template_name = 'dashboard/featured_members/list.html'
    context_object_name = 'members'
    ordering = ['display_order', 'full_name']


class FeaturedMemberCreateView(LoginRequiredMixin, CreateView):
    """Crear nuevo asociado destacado"""
    model = FeaturedMember
    form_class = FeaturedMemberForm
    template_name = 'dashboard/featured_members/form.html'
    success_url = reverse_lazy('featured_member_list')

    def form_valid(self, form):
        messages.success(self.request, 'Asociado destacado creado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Agregar Asociado Destacado'
        context['button_text'] = 'Crear Asociado'
        return context


class FeaturedMemberUpdateView(LoginRequiredMixin, UpdateView):
    """Editar asociado destacado"""
    model = FeaturedMember
    form_class = FeaturedMemberForm
    template_name = 'dashboard/featured_members/form.html'
    success_url = reverse_lazy('featured_member_list')

    def form_valid(self, form):
        messages.success(self.request, 'Asociado destacado actualizado exitosamente.')
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Editar Asociado Destacado'
        context['button_text'] = 'Guardar Cambios'
        return context


class FeaturedMemberDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar asociado destacado"""
    model = FeaturedMember
    template_name = 'dashboard/featured_members/confirm_delete.html'
    success_url = reverse_lazy('featured_member_list')

    def form_valid(self, form):
        messages.success(self.request, 'Asociado destacado eliminado exitosamente.')
        return super().form_valid(form)


# ============================================
# Módulo de Correos / Mailing
# ============================================

class EmailComposeView(LoginRequiredMixin, FormView):
    """Vista para componer y enviar correos"""
    template_name = 'dashboard/emails/compose.html'
    form_class = EmailComposeForm
    success_url = reverse_lazy('email_history')

    def form_valid(self, form):
        recipients = form.get_recipients()
        subject = form.cleaned_data['subject']
        message_content = form.cleaned_data['message']

        # Contexto para la plantilla
        context = {
            'subject': subject,
            'message': message_content,
        }

        # Renderizar plantilla HTML
        html_content = render_to_string('emails/base_email.html', context)

        # Versión texto plano
        text_content = f"{subject}\n\n{message_content}\n\n--\nAsociación Nuclear Colombiana\ninfo@asncol.com"

        success = True
        error_msg = ''

        try:
            # Enviar correo (BCC para privacidad de destinatarios)
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[settings.DEFAULT_FROM_EMAIL],  # A nosotros mismos
                bcc=recipients  # Destinatarios en BCC
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)

        except Exception as e:
            success = False
            error_msg = str(e)

        # Guardar en historial
        SentEmail.objects.create(
            subject=subject,
            message=message_content,
            recipients=', '.join(recipients),
            recipients_count=len(recipients),
            sent_by=self.request.user,
            success=success,
            error_message=error_msg
        )

        if success:
            messages.success(self.request, f'Correo enviado exitosamente a {len(recipients)} destinatario(s).')
        else:
            messages.error(self.request, f'Error al enviar el correo: {error_msg}')

        return super().form_valid(form)


class EmailHistoryView(LoginRequiredMixin, ListView):
    """Lista de correos enviados"""
    model = SentEmail
    template_name = 'dashboard/emails/history.html'
    context_object_name = 'emails'
    ordering = ['-sent_at']
    paginate_by = 20


class EmailDetailView(LoginRequiredMixin, DetailView):
    """Detalle de un correo enviado"""
    model = SentEmail
    template_name = 'dashboard/emails/detail.html'
    context_object_name = 'email'