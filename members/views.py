from django.shortcuts import render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.contrib import messages

from carnets.models import MemberCard
from carnets.utils import generate_card_pdf


class MemberLoginView(LoginView):
    """Login view for regular members (associates)."""
    template_name = 'members/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        user = self.request.user
        # If user is staff/superuser, redirect to admin dashboard
        if user.is_staff or user.is_superuser:
            return '/portal/'
        # Regular users go to member portal
        return '/mi-portal/'


class MemberDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard home for regular members."""
    template_name = 'members/dashboard.html'
    login_url = '/acceso/'

    def dispatch(self, request, *args, **kwargs):
        # If user is staff/superuser, redirect to admin dashboard
        if request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return redirect('/portal/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get user's card if exists
        try:
            context['card'] = MemberCard.objects.get(user=self.request.user)
        except MemberCard.DoesNotExist:
            context['card'] = None
        return context


class MemberCardView(LoginRequiredMixin, TemplateView):
    """View for members to see their digital card."""
    template_name = 'members/card.html'
    login_url = '/acceso/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['card'] = MemberCard.objects.get(user=self.request.user)
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
        return context
