from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid

class MembershipApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pendiente de Revisión')
        UNDER_REVIEW = 'REVIEW', _('En Estudio')
        APPROVED = 'APPROVED', _('Aprobado')
        REJECTED = 'REJECTED', _('Rechazado')
        COMPLETED = 'COMPLETED', _('Vinculado (Usuario Creado)')

    # Identificación única de la solicitud (para URLs seguras más adelante)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    
    # Datos Personales Básicos
    first_name = models.CharField(_('Nombres'), max_length=150)
    last_name = models.CharField(_('Apellidos'), max_length=150)
    email = models.EmailField(_('Correo Electrónico'), unique=True)
    phone = models.CharField(_('Teléfono'), max_length=20, blank=True)

    # Perfil Profesional
    profession = models.CharField(_('Profesión / Título'), max_length=100)
    current_job = models.CharField(_('Cargo Actual'), max_length=100, blank=True)
    institution = models.CharField(_('Empresa / Institución'), max_length=100, blank=True)
    linkedin_url = models.URLField(_('LinkedIn / Perfil Profesional'), blank=True)

    # Motivación y aporte
    contribution_statement = models.TextField(
        _('¿Cómo puedes aportar a la ASNC?'),
        blank=True,
        help_text=_('Cuéntanos brevemente sobre ti, tu experiencia en el sector nuclear y cómo crees que puedes contribuir al crecimiento de la asociación.')
    )

    # Archivos (El CV) - Opcional
    cv_file = models.FileField(
        _('Hoja de Vida (PDF)'),
        upload_to='applications/cvs/',
        blank=True,
        null=True
    )

    # Estado del trámite
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING
    )
    admin_notes = models.TextField(_('Notas Internas del Comité'), blank=True)
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_status_display()}"

    class Meta:
        verbose_name = _('Solicitud de Ingreso')
        verbose_name_plural = _('Solicitudes de Ingreso')
        ordering = ['-created_at']
