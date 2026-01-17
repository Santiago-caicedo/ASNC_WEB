from django.db import models
from django.utils.translation import gettext_lazy as _


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
