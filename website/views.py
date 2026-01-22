from django.views.generic import TemplateView, ListView
from .models import FeaturedMember


class HomeView(TemplateView):
    template_name = 'website/home.html'


class AboutView(ListView):
    """Página Quiénes Somos con asociados destacados"""
    model = FeaturedMember
    template_name = 'website/about.html'
    context_object_name = 'members'

    def get_queryset(self):
        return FeaturedMember.objects.filter(is_active=True).order_by('display_order', 'full_name')


class EventsView(TemplateView):
    """Página de Eventos"""
    template_name = 'website/events.html'


class PowerPointTemplateView(TemplateView):
    """Plantilla PowerPoint ASNC"""
    template_name = 'website/powerpoint_template.html'