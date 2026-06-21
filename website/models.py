from django.db import models
from django.utils.translation import gettext_lazy as _, get_language
from django.utils.text import slugify


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
    is_international = models.BooleanField(
        _('Asociado Internacional'),
        default=False,
        help_text=_('Marcar si es un asociado o colaborador internacional')
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


class NewsArticle(models.Model):
    """Modelo para noticias/blog de la ASNC"""

    class Category(models.TextChoices):
        ASSOCIATION = 'ASSOCIATION', _('De la Asociación')
        NUCLEAR = 'NUCLEAR', _('Temática Nuclear')

    category = models.CharField(
        _('Categoría'),
        max_length=15,
        choices=Category.choices,
        default=Category.NUCLEAR,
        help_text=_('Selecciona si es una noticia de la asociación o sobre temática nuclear')
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
