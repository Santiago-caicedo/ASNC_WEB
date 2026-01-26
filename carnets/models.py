import uuid as uuid_lib
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class MemberCard(models.Model):
    """Digital member card for ASNC associates."""

    class Status(models.TextChoices):
        PENDING_PHOTO = 'PENDING_PHOTO', _('Pendiente de Foto')
        ACTIVE = 'ACTIVE', _('Activo')
        EXPIRED = 'EXPIRED', _('Expirado')
        SUSPENDED = 'SUSPENDED', _('Suspendido')
        CANCELLED = 'CANCELLED', _('Cancelado')

    class Category(models.TextChoices):
        FOUNDER = 'FOUNDER', _('Fundador')
        ASSOCIATE = 'ASSOCIATE', _('Asociado')

    # Unique identifiers
    uuid = models.UUIDField(
        default=uuid_lib.uuid4,
        editable=False,
        unique=True,
        help_text=_('Identificador único para URL de verificación')
    )
    card_number = models.CharField(
        _('Número de Carné'),
        max_length=20,
        unique=True,
        help_text=_('Formato: ASNC-YYYY-NNNN')
    )

    # Relations
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='member_card',
        verbose_name=_('Usuario')
    )
    application = models.OneToOneField(
        'admissions.MembershipApplication',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='member_card',
        verbose_name=_('Solicitud de Ingreso')
    )

    # Card details
    photo = models.ImageField(
        _('Foto'),
        upload_to='carnets/photos/',
        blank=True,
        null=True
    )
    category = models.CharField(
        _('Categoría'),
        max_length=20,
        choices=Category.choices,
        default=Category.ASSOCIATE
    )

    # Validity dates
    issue_date = models.DateField(
        _('Fecha de Emisión'),
        default=timezone.now
    )
    expiry_date = models.DateField(
        _('Fecha de Vencimiento'),
        help_text=_('Por defecto: 31 de diciembre del año de emisión')
    )

    # Status
    status = models.CharField(
        _('Estado'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_PHOTO
    )

    # Photo upload token (for secure link)
    photo_token = models.UUIDField(
        default=uuid_lib.uuid4,
        editable=False,
        unique=True,
        help_text=_('Token único para subir foto')
    )
    photo_token_used = models.BooleanField(
        _('Token de foto usado'),
        default=False
    )

    # Administrative
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_cards',
        verbose_name=_('Emitido por')
    )
    suspension_reason = models.TextField(
        _('Motivo de suspensión'),
        blank=True
    )

    # Audit
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Carné Digital')
        verbose_name_plural = _('Carnés Digitales')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.card_number} - {self.user.get_full_name()}"

    def save(self, *args, **kwargs):
        # Auto-set expiry date to Dec 31 of issue year if not set
        if not self.expiry_date:
            issue_year = self.issue_date.year if self.issue_date else timezone.now().year
            self.expiry_date = timezone.datetime(issue_year, 12, 31).date()
        super().save(*args, **kwargs)

    @classmethod
    def generate_card_number(cls):
        """Generate next card number in sequence: ASNC-YYYY-NNNN"""
        current_year = timezone.now().year
        prefix = f"ASNC-{current_year}-"

        # Get the last card number for this year
        last_card = cls.objects.filter(
            card_number__startswith=prefix
        ).order_by('-card_number').first()

        if last_card:
            # Extract the sequence number and increment
            try:
                last_seq = int(last_card.card_number.split('-')[-1])
                new_seq = last_seq + 1
            except ValueError:
                new_seq = 1
        else:
            new_seq = 1

        return f"{prefix}{new_seq:04d}"

    @property
    def is_valid(self):
        """Check if the card is currently valid."""
        if self.status != self.Status.ACTIVE:
            return False
        if self.expiry_date < timezone.now().date():
            return False
        return True

    @property
    def full_name(self):
        """Get the cardholder's full name."""
        return self.user.get_full_name()

    def get_verification_url(self):
        """Get the public verification URL."""
        from django.urls import reverse
        return reverse('carnets:verificar', kwargs={'uuid': self.uuid})


class CardVerification(models.Model):
    """Log of card verification scans."""

    card = models.ForeignKey(
        MemberCard,
        on_delete=models.CASCADE,
        related_name='verifications',
        verbose_name=_('Carné')
    )
    verified_at = models.DateTimeField(
        _('Verificado en'),
        auto_now_add=True
    )
    ip_address = models.GenericIPAddressField(
        _('Dirección IP'),
        null=True,
        blank=True
    )
    user_agent = models.TextField(
        _('User Agent'),
        blank=True
    )

    class Meta:
        verbose_name = _('Verificación de Carné')
        verbose_name_plural = _('Verificaciones de Carnés')
        ordering = ['-verified_at']

    def __str__(self):
        return f"Verificación de {self.card.card_number} - {self.verified_at}"
