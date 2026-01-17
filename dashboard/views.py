from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from admissions.models import MembershipApplication
from website.models import FeaturedMember
from .forms import FeaturedMemberForm


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