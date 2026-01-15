from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from admissions.models import MembershipApplication

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
        context['members_count'] = 0 # Todavía no tenemos tabla de miembros, pero dejamos el espacio
        return context