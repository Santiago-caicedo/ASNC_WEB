from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        MEMBER = 'MEMBER', 'Asociado'
        ADMIN = 'ADMIN', 'Administrador'

    email = models.EmailField('dirección de correo electrónico', unique=True)

    role = models.CharField(
        'Rol',
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
        db_index=True,
    )

    can_edit_news = models.BooleanField(
        'Puede gestionar noticias',
        default=False,
        help_text='Permite al usuario crear, editar y eliminar noticias desde el portal.',
    )

    # Datos de contacto
    phone = models.CharField('Teléfono', max_length=20, blank=True)

    # Perfil profesional
    profession = models.CharField('Profesión / Título', max_length=100, blank=True)
    current_job = models.CharField('Cargo Actual', max_length=100, blank=True)
    institution = models.CharField('Empresa / Institución', max_length=150, blank=True)
    linkedin_url = models.URLField('LinkedIn', blank=True)
    bio = models.TextField('Biografía Profesional', blank=True,
                          help_text='Breve descripción de tu trayectoria profesional')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email

    @property
    def is_admin(self):
        """Check if user has admin role or is superuser."""
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def is_news_editor(self):
        """Check if user can manage news articles."""
        return self.can_edit_news

    @property
    def profile_completion(self):
        """Calculate profile completion percentage."""
        fields = ['first_name', 'last_name', 'phone', 'profession',
                  'current_job', 'institution', 'linkedin_url', 'bio']
        filled = sum(1 for f in fields if getattr(self, f, None))
        return int((filled / len(fields)) * 100)