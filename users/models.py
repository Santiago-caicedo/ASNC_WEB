from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField('dirección de correo electrónico', unique=True)
    
    # Aquí podremos añadir roles o flags más adelante si es necesario
    # Por ahora, con heredar de AbstractUser es suficiente para "futurizar" el proyecto.

    USERNAME_FIELD = 'email' 
    # Usaremos el email para hacer login, no el username. Más profesional.
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    def __str__(self):
        return self.email