from django.db import models
from django.utils.translation import gettext_lazy as _
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

    # Professional info
    profession = models.CharField(
        _('Profesión'),
        max_length=150,
        help_text=_('Ej: Ingeniero Nuclear, Físico Médico')
    )
    professional_trajectory = models.TextField(
        _('Trayectoria Profesional'),
        help_text=_('Descripción de la experiencia y logros profesionales')
    )

    # Social
    linkedin_url = models.URLField(_('Perfil de LinkedIn'), blank=True)

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


class NewsArticle(models.Model):
    """Modelo para noticias/blog de la ASNC"""

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
