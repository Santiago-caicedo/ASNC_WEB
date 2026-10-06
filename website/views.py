import json
import logging
from email.utils import formataddr
from datetime import timezone as dt_timezone
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.core.mail import EmailMultiAlternatives
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.cache import cache_control
from django.views.generic import TemplateView, ListView, DetailView
from django.views.generic.edit import FormView

from django.shortcuts import get_object_or_404

from .forms import ContactForm
from .models import Event, FeaturedMember, NewsArticle, NewsCategory

logger = logging.getLogger(__name__)

# Datos del Observatorio ENSO, generados por scripts/generar_datos_enso.py.
ENSO_DATA_PATH = Path(__file__).resolve().parent / 'data' / 'enso.json'


def enso_data_version():
    """Versión del archivo de datos ENSO (su fecha de modificación)."""
    try:
        return int(ENSO_DATA_PATH.stat().st_mtime)
    except OSError:
        return 0


@cache_control(max_age=60 * 60 * 24, public=True)
def enso_data(request):
    """Serie ONI, episodios y resultados del modelo, para el tablero de la home.

    Se sirve desde el mismo dominio (y no como archivo estático) para que el
    `fetch` del tablero no dependa de la configuración CORS del bucket S3.
    El contenido es estático, así que se cachea en memoria tras la primera
    lectura y se marca como cacheable por 24 horas en el navegador. La portada
    pide la URL con `?v=<versión del archivo>`, de modo que al regenerar los
    datos el navegador no reutiliza la copia anterior.
    """
    cache_key = f'enso_data_json:{enso_data_version()}'
    payload = cache.get(cache_key)
    if payload is None:
        try:
            payload = ENSO_DATA_PATH.read_text(encoding='utf-8')
        except OSError:
            logger.exception('No se pudo leer el archivo de datos ENSO')
            raise Http404('Datos ENSO no disponibles')
        cache.set(cache_key, payload, 60 * 60 * 24)
    return JsonResponse(json.loads(payload))


class HomeView(TemplateView):
    template_name = 'website/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['enso_version'] = enso_data_version()
        # Recuadro del hero: el evento más próximo; sin eventos, las noticias.
        context['next_event'] = Event.objects.upcoming().first()
        published = NewsArticle.objects.filter(
            is_published=True
        ).select_related('category')
        # Barra lateral: noticias de la categoría "De la Asociación".
        context['news_association'] = published.filter(
            category__slug='de-la-asociacion'
        )[:4]
        # Sección principal: últimas noticias del resto de categorías
        # (incluye cualquier categoría nueva, p. ej. "Mundial Nuclear").
        context['news_nuclear'] = published.exclude(
            category__slug='de-la-asociacion'
        )[:4]
        return context


class AboutView(ListView):
    """Página Quiénes Somos con asociados destacados"""
    model = FeaturedMember
    template_name = 'website/about.html'
    context_object_name = 'members'

    def get_queryset(self):
        return FeaturedMember.objects.filter(is_active=True, is_advisory=False).order_by('display_order', 'full_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['advisory_members'] = FeaturedMember.objects.filter(
            is_active=True, is_advisory=True
        ).order_by('display_order', 'full_name')
        return context


class AdvisoryCommitteeView(ListView):
    """Página dedicada al Comité Asesor (nacional e internacional)"""
    model = FeaturedMember
    template_name = 'website/comite_asesor.html'
    context_object_name = 'members'

    def get_queryset(self):
        return FeaturedMember.objects.filter(
            is_active=True, is_advisory=True
        ).order_by('display_order', 'full_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        countries = {m.country for m in context['members'] if m.country}
        context['countries_count'] = len(countries)
        return context


class EventsView(TemplateView):
    """Agenda pública: el próximo evento, los siguientes por mes y los anteriores."""
    template_name = 'website/events.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        upcoming = list(Event.objects.upcoming())
        context['next_event'] = upcoming[0] if upcoming else None
        context['later_events'] = upcoming[1:]
        context['past_events'] = Event.objects.past()[:6]
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = 'website/event_detail.html'
    context_object_name = 'event'

    def get_queryset(self):
        return Event.objects.published()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['other_events'] = Event.objects.upcoming().exclude(pk=self.object.pk)[:3]
        return context


def _ics_escape(text):
    return (text or '').replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\n', '\\n')


def event_ics(request, slug):
    """Archivo .ics para agregar el evento al calendario del visitante."""
    event = get_object_or_404(Event.objects.published(), slug=slug)
    fmt = '%Y%m%dT%H%M%SZ'
    utc = dt_timezone.utc
    url = request.build_absolute_uri(event.get_absolute_url())
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//ASNC//Eventos//ES',
        'CALSCALE:GREGORIAN',
        'BEGIN:VEVENT',
        f'UID:evento-{event.pk}@asncol.com',
        f'DTSTAMP:{timezone.now().astimezone(utc).strftime(fmt)}',
        f'DTSTART:{event.starts_at.astimezone(utc).strftime(fmt)}',
        f'DTEND:{event.end.astimezone(utc).strftime(fmt)}',
        f'SUMMARY:{_ics_escape(event.title)}',
        f'DESCRIPTION:{_ics_escape(event.summary + chr(10) + chr(10) + url)}',
        f'LOCATION:{_ics_escape(event.location)}',
        f'URL:{url}',
        'END:VEVENT',
        'END:VCALENDAR',
    ]
    response = HttpResponse('\r\n'.join(lines) + '\r\n', content_type='text/calendar; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{event.slug}.ics"'
    return response


class ContactView(FormView):
    """Página de Contacto: formulario que guarda el mensaje y notifica por correo."""
    template_name = 'website/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_token'] = TimestampSigner().sign('contact')
        return context

    def _client_ip(self):
        xff = self.request.META.get('HTTP_X_FORWARDED_FOR', '')
        if xff:
            return xff.split(',')[0].strip()
        return self.request.META.get('REMOTE_ADDR')

    def form_valid(self, form):
        # Control de velocidad: un humano no diligencia el formulario en <3s.
        # Es la capa que ya usa el formulario de solicitudes y que faltaba aquí.
        token = form.cleaned_data.get('form_token', '')
        if not token:
            form.add_error(None, _('Error en el formulario. Por favor recarga la página.'))
            return self.form_invalid(form)
        signer = TimestampSigner()
        try:
            signer.unsign(token, max_age=86400)
        except (BadSignature, SignatureExpired):
            form.add_error(None, _('La sesión del formulario ha expirado. Por favor recarga la página.'))
            return self.form_invalid(form)
        try:
            signer.unsign(token, max_age=3)
        except SignatureExpired:
            pass  # Tardó más de 3s: comportamiento humano esperado
        except BadSignature:
            form.add_error(None, _('Error en el formulario. Por favor recarga la página.'))
            return self.form_invalid(form)
        else:
            form.add_error(None, _('Por favor toma un momento para completar el formulario.'))
            return self.form_invalid(form)

        ip = self._client_ip()
        cache_key = f'contact_rate_{ip}'
        if cache.get(cache_key, 0) >= 5:
            messages.error(self.request, _(
                'Has enviado demasiados mensajes. Por favor intenta más tarde.'))
            return redirect('contact')

        contact = form.save(commit=False)
        contact.ip_address = ip
        contact.save()
        cache.set(cache_key, cache.get(cache_key, 0) + 1, 3600)

        # Notificación por correo (fuera de cualquier transacción; no rompe el flujo)
        try:
            subject = f'[Contacto web] {contact.subject}'
            body = (
                f'Nombre: {contact.name}\n'
                f'Correo: {contact.email}\n\n'
                f'Mensaje:\n{contact.message}'
            )
            email = EmailMultiAlternatives(
                subject, body,
                formataddr(('Asociación Nuclear Colombiana', settings.DEFAULT_FROM_EMAIL)),
                [settings.DEFAULT_FROM_EMAIL],
                reply_to=[contact.email],
            )
            email.send(fail_silently=False)
        except Exception:
            logger.exception('Fallo al enviar el correo de contacto')

        messages.success(self.request, _(
            'Tu mensaje ha sido enviado correctamente. ¡Gracias por escribirnos!'))
        return super().form_valid(form)


class PowerPointTemplateView(TemplateView):
    """Plantilla PowerPoint ASNC"""
    template_name = 'website/powerpoint_template.html'


class PrivacyPolicyView(TemplateView):
    """Política de Privacidad y Tratamiento de Datos"""
    template_name = 'website/privacy_policy.html'


def get_active_news_categories():
    """Categorías activas que tienen al menos una noticia publicada."""
    return NewsCategory.objects.filter(
        is_active=True,
        articles__is_published=True,
    ).distinct()


class NewsListView(ListView):
    """Listado público de noticias"""
    model = NewsArticle
    template_name = 'website/news/list.html'
    context_object_name = 'articles'
    paginate_by = 9

    def get_queryset(self):
        return NewsArticle.objects.filter(
            is_published=True
        ).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = get_active_news_categories()
        return context


class NewsCategoryDetailView(ListView):
    """Listado público de noticias filtradas por categoría"""
    model = NewsArticle
    template_name = 'website/news/list.html'
    context_object_name = 'articles'
    paginate_by = 9

    def get_queryset(self):
        self.category = get_object_or_404(
            NewsCategory, slug=self.kwargs['slug'], is_active=True
        )
        return NewsArticle.objects.filter(
            is_published=True, category=self.category
        ).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = get_active_news_categories()
        context['current_category'] = self.category
        return context


class NewsDetailView(DetailView):
    """Detalle público de una noticia"""
    model = NewsArticle
    template_name = 'website/news/detail.html'
    context_object_name = 'article'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        return NewsArticle.objects.filter(is_published=True).select_related('category')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recent_articles'] = NewsArticle.objects.filter(
            is_published=True
        ).exclude(pk=self.object.pk).select_related('category')[:3]
        return context