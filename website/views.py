from django.views.generic import TemplateView, ListView, DetailView
from .models import FeaturedMember, NewsArticle


class HomeView(TemplateView):
    template_name = 'website/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        published = NewsArticle.objects.filter(is_published=True)
        context['news_association'] = published.filter(
            category=NewsArticle.Category.ASSOCIATION
        )[:4]
        context['news_nuclear'] = published.filter(
            category=NewsArticle.Category.NUCLEAR
        )[:4]
        return context


class AboutView(ListView):
    """Página Quiénes Somos con asociados destacados"""
    model = FeaturedMember
    template_name = 'website/about.html'
    context_object_name = 'members'

    def get_queryset(self):
        return FeaturedMember.objects.filter(is_active=True, is_international=False).order_by('display_order', 'full_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['international_members'] = FeaturedMember.objects.filter(
            is_active=True, is_international=True
        ).order_by('display_order', 'full_name')
        return context


class EventsView(TemplateView):
    """Página de Eventos"""
    template_name = 'website/events.html'


class PowerPointTemplateView(TemplateView):
    """Plantilla PowerPoint ASNC"""
    template_name = 'website/powerpoint_template.html'


class PrivacyPolicyView(TemplateView):
    """Política de Privacidad y Tratamiento de Datos"""
    template_name = 'website/privacy_policy.html'


class NewsListView(ListView):
    """Listado público de noticias"""
    model = NewsArticle
    template_name = 'website/news/list.html'
    context_object_name = 'articles'
    paginate_by = 9

    def get_queryset(self):
        return NewsArticle.objects.filter(is_published=True)


class NewsDetailView(DetailView):
    """Detalle público de una noticia"""
    model = NewsArticle
    template_name = 'website/news/detail.html'
    context_object_name = 'article'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return NewsArticle.objects.filter(is_published=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_articles'] = NewsArticle.objects.filter(
            is_published=True
        ).exclude(pk=self.object.pk)[:3]
        return context