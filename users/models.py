from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField('dirección de correo electrónico', unique=True)

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
    def profile_completion(self):
        """Calculate profile completion percentage."""
        fields = ['first_name', 'last_name', 'phone', 'profession',
                  'current_job', 'institution', 'linkedin_url', 'bio']
        filled = sum(1 for f in fields if getattr(self, f, None))
        return int((filled / len(fields)) * 100)