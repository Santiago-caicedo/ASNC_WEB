from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Event


class StaticViewSitemap(Sitemap):
    """Sitemap para páginas estáticas del sitio público"""
    priority = 0.8
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return ['home', 'about', 'events', 'contact', 'application_create']

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        priorities = {
            'home': 1.0,
            'about': 0.8,
            'application_create': 0.9,
            'events': 0.7,
            'contact': 0.7,
        }
        return priorities.get(item, 0.5)


class HomeSitemap(Sitemap):
    """Sitemap específico para la página principal con mayor prioridad"""
    priority = 1.0
    changefreq = 'daily'
    protocol = 'https'

    def items(self):
        return ['home']

    def location(self, item):
        return reverse(item)


class EventSitemap(Sitemap):
    """Eventos publicados (próximos y anteriores)."""
    priority = 0.7
    changefreq = 'weekly'
    protocol = 'https'

    def items(self):
        return Event.objects.published().order_by('-starts_at')

    def lastmod(self, obj):
        return obj.updated_at
