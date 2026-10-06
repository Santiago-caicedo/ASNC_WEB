from datetime import datetime, time

from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, get_language
from django.utils.text import slugify

from .countries import COUNTRIES


class FeaturedMember(models.Model):
    """Modelo para los asociados destacados que aparecen en la página Quiénes Somos"""

    # Personal info
    full_name = models.CharField(_('Nombre Completo'), max_length=200)
    photo = models.ImageField(_('Foto'), upload_to='featured_members/')

    # Association role
    association_position = models.CharField(
        _('Cargo en la Asociación'),
        max_length=150,
        help_text=_('Ej: Presidente, Vicepresidente, Director Científico')
    )
    association_position_en = models.CharField(
        _('Cargo en la Asociación (inglés)'),
        max_length=150, blank=True,
        help_text=_('Versión en inglés. Si se deja vacío, se muestra el español.')
    )

    # Professional info
    profession = models.CharField(
        _('Profesión'),
        max_length=150,
        help_text=_('Ej: Ingeniero Nuclear, Físico Médico')
    )
    profession_en = models.CharField(
        _('Profesión (inglés)'),
        max_length=150, blank=True,
        help_text=_('Versión en inglés. Si se deja vacío, se muestra el español.')
    )
    professional_trajectory = models.TextField(
        _('Trayectoria Profesional'),
        help_text=_('Descripción de la experiencia y logros profesionales')
    )
    professional_trajectory_en = models.TextField(
        _('Trayectoria Profesional (inglés)'),
        blank=True,
        help_text=_('Versión en inglés. Si se deja vacío, se muestra el español.')
    )

    # Social
    linkedin_url = models.URLField(_('Perfil de LinkedIn'), blank=True)

    # Classification
    is_advisory = models.BooleanField(
        _('Comité Asesor'),
        default=False,
        help_text=_('Marcar si hace parte del Comité Asesor')
    )
    country = models.CharField(
        _('País'),
        max_length=2,
        blank=True,
        choices=COUNTRIES,
        help_text=_(
            'País del miembro del Comité Asesor (se muestra con su bandera). '
            'Colombia lo ubica en el comité nacional; cualquier otro país, en el internacional.'
        )
    )

    # Display control
    is_active = models.BooleanField(_('Activo'), default=True)
    display_order = models.PositiveIntegerField(
        _('Orden de visualización'),
        default=0,
        help_text=_('Los asociados se mostrarán ordenados de menor a mayor')
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Asociado Destacado')
        verbose_name_plural = _('Asociados Destacados')
        ordering = ['display_order', 'full_name']

    def __str__(self):
        return f"{self.full_name} - {self.association_position}"

    def _localized(self, es_value, en_value):
        """Devuelve la versión EN si el idioma activo es inglés y existe; si no, ES."""
        lang = get_language() or ''
        if lang.startswith('en') and en_value:
            return en_value
        return es_value

    @property
    def display_position(self):
        return self._localized(self.association_position, self.association_position_en)

    @property
    def display_profession(self):
        return self._localized(self.profession, self.profession_en)

    @property
    def display_trajectory(self):
        return self._localized(self.professional_trajectory, self.professional_trajectory_en)

    @property
    def is_national_advisor(self):
        """El Comité Asesor se divide por país: Colombia es el comité nacional."""
        return self.country == 'CO'

    @property
    def country_name(self):
        return self.get_country_display() if self.country else ''

    @property
    def country_flag_url(self):
        """URL de la bandera del país (flagcdn.com, código ISO en minúsculas)."""
        if self.country:
            return f'https://flagcdn.com/w40/{self.country.lower()}.png'
        return ''


class NewsCategory(models.Model):
    """Categoría de noticias, gestionable desde el panel de administración."""

    name = models.CharField(_('Nombre'), max_length=100, unique=True)
    slug = models.SlugField(_('Slug'), max_length=120, unique=True, blank=True)
    description = models.CharField(
        _('Descripción'),
        max_length=200,
        blank=True,
        help_text=_('Texto opcional que se muestra en la página de la categoría')
    )
    is_active = models.BooleanField(_('Activa'), default=True)
    display_order = models.PositiveIntegerField(_('Orden'), default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Categoría de Noticia')
        verbose_name_plural = _('Categorías de Noticias')
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while NewsCategory.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def published_count(self):
        return self.articles.filter(is_published=True).count()


class NewsArticle(models.Model):
    """Modelo para noticias/blog de la ASNC"""

    category = models.ForeignKey(
        'NewsCategory',
        on_delete=models.PROTECT,
        null=True,
        related_name='articles',
        verbose_name=_('Categoría'),
        help_text=_('Categoría a la que pertenece la noticia')
    )
    title = models.CharField(_('Título'), max_length=255)
    slug = models.SlugField(_('Slug'), max_length=280, unique=True, blank=True)
    cover_image = models.ImageField(_('Imagen de portada'), upload_to='news/')
    excerpt = models.TextField(
        _('Extracto'),
        max_length=300,
        help_text=_('Resumen corto que aparece en el listado (máx. 300 caracteres)')
    )
    content = models.TextField(
        _('Contenido'),
        help_text=_('Contenido completo de la noticia. Se admite HTML básico.')
    )
    author = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Autor'),
        related_name='news_articles'
    )
    is_published = models.BooleanField(_('Publicado'), default=False)
    published_at = models.DateTimeField(_('Fecha de publicación'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Noticia')
        verbose_name_plural = _('Noticias')
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while NewsArticle.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        if self.is_published and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class ContactMessage(models.Model):
    """Mensaje enviado desde el formulario público de Contacto."""

    name = models.CharField(_('Nombre'), max_length=150)
    email = models.EmailField(_('Correo electrónico'))
    subject = models.CharField(_('Asunto'), max_length=200)
    message = models.TextField(_('Mensaje'))

    is_read = models.BooleanField(_('Leído'), default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Mensaje de Contacto')
        verbose_name_plural = _('Mensajes de Contacto')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} — {self.subject}'


class EventQuerySet(models.QuerySet):
    """Un evento sin hora de fin se considera vigente hasta el final de su día."""

    @staticmethod
    def _not_ended():
        return (
            models.Q(ends_at__gte=timezone.now())
            | models.Q(ends_at__isnull=True, starts_at__date__gte=timezone.localdate())
        )

    def published(self):
        return self.filter(is_published=True)

    def not_ended(self):
        return self.filter(self._not_ended())

    def ended(self):
        return self.exclude(self._not_ended())

    def upcoming(self):
        """Publicados que aún no terminan, del más próximo al más lejano."""
        return self.published().not_ended().order_by('starts_at')

    def past(self):
        """Publicados que ya terminaron, del más reciente al más antiguo."""
        return self.published().ended().order_by('-starts_at')


class Event(models.Model):
    """Evento público de la ASNC (conferencias, webinars, talleres...).

    Lo crea el superadmin desde /portal/eventos/. El más próximo se muestra en
    el recuadro del hero de la portada.
    """

    class EventType(models.TextChoices):
        CONFERENCE = 'CONFERENCE', _('Conferencia')
        WEBINAR = 'WEBINAR', _('Webinar')
        WORKSHOP = 'WORKSHOP', _('Taller')
        NETWORKING = 'NETWORKING', _('Encuentro')
        OTHER = 'OTHER', _('Evento')

    class Modality(models.TextChoices):
        IN_PERSON = 'IN_PERSON', _('Presencial')
        VIRTUAL = 'VIRTUAL', _('Virtual')
        HYBRID = 'HYBRID', _('Híbrido')

    title = models.CharField(_('Título'), max_length=200)
    slug = models.SlugField(_('Slug'), max_length=220, unique=True, blank=True)
    event_type = models.CharField(
        _('Tipo de evento'), max_length=20,
        choices=EventType.choices, default=EventType.CONFERENCE,
    )
    modality = models.CharField(
        _('Modalidad'), max_length=20,
        choices=Modality.choices, default=Modality.IN_PERSON,
    )
    starts_at = models.DateTimeField(_('Inicio'))
    ends_at = models.DateTimeField(
        _('Fin'), null=True, blank=True,
        help_text=_('Opcional. Sin hora de fin, el evento se muestra como próximo hasta el final de su día.'),
    )
    location = models.CharField(
        _('Lugar'), max_length=200, blank=True,
        help_text=_('En eventos virtuales, la plataforma (Zoom, Meet, YouTube...).'),
    )
    summary = models.CharField(
        _('Resumen'), max_length=280,
        help_text=_('Una o dos frases. Se muestran en la portada y en la agenda.'),
    )
    description = models.TextField(
        _('Descripción'), blank=True,
        help_text=_('Programa, ponentes, requisitos. Texto simple: los saltos de línea se respetan.'),
    )
    cover_image = models.ImageField(_('Imagen'), upload_to='events/', blank=True)
    registration_url = models.URLField(
        _('Enlace de inscripción'), blank=True,
        help_text=_('Formulario de inscripción o enlace de acceso a la transmisión.'),
    )
    is_published = models.BooleanField(
        _('Publicado'), default=True,
        help_text=_('Desmárcalo para guardarlo como borrador sin mostrarlo en el sitio.'),
    )
    created_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='events', verbose_name=_('Creado por'),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventQuerySet.as_manager()

    class Meta:
        verbose_name = _('Evento')
        verbose_name_plural = _('Eventos')
        ordering = ['-starts_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:200] or 'evento'
            slug = base_slug
            counter = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('event_detail', args=[self.slug])

    @property
    def end(self):
        """Fin efectivo: la hora de fin o, si no hay, el final del día de inicio."""
        if self.ends_at:
            return self.ends_at
        day = timezone.localtime(self.starts_at).date()
        return timezone.make_aware(datetime.combine(day, time.max))

    @property
    def is_past(self):
        return self.end < timezone.now()

    @property
    def is_ongoing(self):
        now = timezone.now()
        return self.starts_at <= now <= self.end

    @property
    def days_until(self):
        """Días de calendario que faltan para el inicio (0 = hoy)."""
        return (timezone.localtime(self.starts_at).date() - timezone.localdate()).days

    @property
    def start_month(self):
        """Primer día del mes de inicio (hora local), para agrupar la agenda por mes."""
        return timezone.localtime(self.starts_at).date().replace(day=1)

    @property
    def is_multiday(self):
        if not self.ends_at:
            return False
        return timezone.localtime(self.ends_at).date() != timezone.localtime(self.starts_at).date()
