import re
import uuid as uuid_lib

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class Convocatoria(models.Model):
    """
    A public call for applications. Admins define the metadata and a list of
    dynamic form fields. Interested users submit the form via a public link.
    """

    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True)

    title = models.CharField(_('Título'), max_length=200)
    slug = models.SlugField(_('Slug'), max_length=230, unique=True, blank=True)
    description = models.TextField(
        _('Descripción'),
        help_text=_('Información visible arriba del formulario. Admite saltos de línea.')
    )
    cover_image = models.ImageField(
        _('Imagen de portada'),
        upload_to='convocatorias/',
        blank=True,
        null=True,
        help_text=_('Opcional. Se muestra arriba del título en el formulario público.')
    )

    is_active = models.BooleanField(_('Activa'), default=True)
    opens_at = models.DateTimeField(_('Fecha de apertura'), null=True, blank=True)
    closes_at = models.DateTimeField(_('Fecha de cierre'), null=True, blank=True)

    success_message = models.TextField(
        _('Mensaje de confirmación'),
        blank=True,
        default='¡Gracias por tu interés! Hemos recibido tu inscripción correctamente.',
        help_text=_('Texto que verá el usuario después de enviar el formulario.')
    )

    created_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='convocatorias_created',
        verbose_name=_('Creada por')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Convocatoria')
        verbose_name_plural = _('Convocatorias')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:220] or 'convocatoria'
            slug = base_slug
            counter = 1
            while Convocatoria.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('convocatorias:detail', kwargs={'slug': self.slug})

    @property
    def is_open(self):
        """Whether the convocatoria currently accepts submissions."""
        from django.utils import timezone
        if not self.is_active:
            return False
        now = timezone.now()
        if self.opens_at and now < self.opens_at:
            return False
        if self.closes_at and now > self.closes_at:
            return False
        return True

    # Correo "razonable": sin espacios ni separadores, con arroba y dominio con punto.
    EMAIL_RE = re.compile(r'^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$')

    def email_report(self):
        """Correos de las inscripciones y explicación de las que no aportan uno.

        Devuelve un dict con:
          - ``emails``: correos únicos, en orden de llegada (para Calendar).
          - ``duplicadas``: inscripciones cuyo correo ya apareció antes, con el
            correo repetido (una misma persona inscrita más de una vez).
          - ``sin_correo``: inscripciones sin ninguna respuesta con forma de correo.

        Primero se miran los campos de tipo correo; como respaldo se acepta
        cualquier respuesta que tenga forma de correo, por si el formulario lo
        pidió en un campo de texto. Las mayúsculas no cuentan al deduplicar.
        """
        email_labels = list(self.fields.filter(field_type=ConvocatoriaField.FieldType.EMAIL)
                            .values_list('label', flat=True))
        seen, emails, duplicadas, sin_correo = set(), [], [], []

        for sub in self.submissions.order_by('submitted_at'):
            data = sub.data or {}
            candidatos = [data.get(l) for l in email_labels] + list(data.values())
            valido = None
            for value in candidatos:
                v = value.strip() if isinstance(value, str) else ''
                if self.EMAIL_RE.match(v):
                    valido = v
                    break
            if valido is None:
                sin_correo.append(sub)
            elif valido.lower() in seen:
                duplicadas.append((sub, valido))
            else:
                seen.add(valido.lower())
                emails.append(valido)
        return {'emails': emails, 'duplicadas': duplicadas, 'sin_correo': sin_correo}

    def collect_emails(self):
        """Solo la lista de correos únicos (ver ``email_report``)."""
        return self.email_report()['emails']

    @property
    def submissions_count(self):
        return self.submissions.count()


class ConvocatoriaField(models.Model):
    """Dynamic field belonging to a Convocatoria form."""

    class FieldType(models.TextChoices):
        TEXT = 'TEXT', _('Texto corto')
        TEXTAREA = 'TEXTAREA', _('Párrafo')
        EMAIL = 'EMAIL', _('Correo electrónico')
        PHONE = 'PHONE', _('Teléfono')
        NUMBER = 'NUMBER', _('Número')
        DATE = 'DATE', _('Fecha')
        SELECT = 'SELECT', _('Lista desplegable')
        CHECKBOX = 'CHECKBOX', _('Casilla (sí/no)')
        FILE = 'FILE', _('Archivo')

    convocatoria = models.ForeignKey(
        Convocatoria,
        on_delete=models.CASCADE,
        related_name='fields'
    )
    label = models.CharField(_('Etiqueta'), max_length=150)
    field_type = models.CharField(
        _('Tipo de campo'),
        max_length=15,
        choices=FieldType.choices,
        default=FieldType.TEXT
    )
    required = models.BooleanField(_('Obligatorio'), default=True)
    help_text = models.CharField(_('Texto de ayuda'), max_length=255, blank=True)
    placeholder = models.CharField(_('Placeholder'), max_length=120, blank=True)
    options = models.TextField(
        _('Opciones'),
        blank=True,
        help_text=_('Solo para lista desplegable. Una opción por línea.')
    )
    order = models.PositiveIntegerField(_('Orden'), default=0)

    class Meta:
        verbose_name = _('Campo de Convocatoria')
        verbose_name_plural = _('Campos de Convocatoria')
        ordering = ['order', 'pk']

    def __str__(self):
        return f'{self.label} ({self.get_field_type_display()})'

    @property
    def options_list(self):
        if not self.options:
            return []
        return [line.strip() for line in self.options.splitlines() if line.strip()]

    @property
    def input_name(self):
        """Name used for the form input (stable based on pk)."""
        return f'field_{self.pk}'


class ConvocatoriaSubmission(models.Model):
    """A single submission to a Convocatoria form."""

    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True)
    convocatoria = models.ForeignKey(
        Convocatoria,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    data = models.JSONField(
        _('Respuestas'),
        default=dict,
        help_text=_('Diccionario con {"label": "valor"} de cada campo.')
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = _('Inscripción')
        verbose_name_plural = _('Inscripciones')
        ordering = ['-submitted_at']

    def __str__(self):
        return f'Inscripción {self.uuid} — {self.convocatoria.title}'

    @property
    def summary(self):
        """First couple of field values to show in lists."""
        if not self.data:
            return ''
        first_values = list(self.data.values())[:2]
        return ' — '.join(str(v) for v in first_values if v)


def submission_file_path(instance, filename):
    return f'convocatorias/submissions/{instance.submission.convocatoria_id}/{instance.submission.uuid}/{filename}'


class ConvocatoriaSubmissionFile(models.Model):
    """File uploaded as part of a submission (one per FILE-type field)."""

    submission = models.ForeignKey(
        ConvocatoriaSubmission,
        on_delete=models.CASCADE,
        related_name='files'
    )
    field_label = models.CharField(max_length=150)
    file = models.FileField(upload_to=submission_file_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

    def __str__(self):
        return f'{self.field_label} — {self.file.name}'
