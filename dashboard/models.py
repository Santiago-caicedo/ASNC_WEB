from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class SentEmail(models.Model):
    """Historial de correos enviados desde el dashboard"""

    subject = models.CharField(_('Asunto'), max_length=255)
    message = models.TextField(_('Mensaje'))
    recipients = models.TextField(
        _('Destinatarios'),
        help_text=_('Lista de correos separados por coma')
    )
    recipients_count = models.PositiveIntegerField(_('Cantidad de destinatarios'), default=0)

    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_('Enviado por')
    )
    sent_at = models.DateTimeField(_('Fecha de envío'), auto_now_add=True)

    # Para tracking básico
    success = models.BooleanField(_('Enviado exitosamente'), default=True)
    error_message = models.TextField(_('Mensaje de error'), blank=True)

    class Meta:
        verbose_name = _('Correo Enviado')
        verbose_name_plural = _('Correos Enviados')
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.subject} - {self.sent_at.strftime('%d/%m/%Y %H:%M')}"

    def get_recipients_list(self):
        """Retorna lista de destinatarios"""
        return [email.strip() for email in self.recipients.split(',') if email.strip()]
