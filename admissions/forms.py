import re

from django import forms
from django.core.exceptions import ValidationError

from config.antispam import (
    BLOCKED_EMAIL_DOMAINS, validate_email_domain, validate_no_spam,
)

from .models import MembershipApplication

class MembershipApplicationForm(forms.ModelForm):
    # Honeypot - bots fill this, humans don't see it
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    # Timestamp for speed check (injected by the view)
    form_token = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = MembershipApplication
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'profession', 'contribution_statement'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'placeholder': 'Ej: María',
                'class': 'form-control form-control-lg'
            }),
            'last_name': forms.TextInput(attrs={
                'placeholder': 'Ej: González',
                'class': 'form-control form-control-lg'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'tu@email.com',
                'class': 'form-control form-control-lg'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'Ej: +57 300 123 4567',
                'class': 'form-control form-control-lg'
            }),
            'profession': forms.TextInput(attrs={
                'placeholder': 'Ej: Ingeniero, Médico, Abogado, Comunicador',
                'class': 'form-control form-control-lg'
            }),
            'contribution_statement': forms.Textarea(attrs={
                'placeholder': 'Cuéntanos sobre tu trayectoria profesional, tu interés en el sector nuclear y cómo crees que puedes contribuir al crecimiento de la ASNC...',
                'class': 'form-control form-control-lg',
                'rows': 4
            }),
        }
        labels = {
            'contribution_statement': '¿Cómo puedes aportar a la ASNC?'
        }

    def clean_website(self):
        """Honeypot: if filled, it's a bot."""
        if self.cleaned_data.get('website'):
            raise ValidationError('Error en el formulario.')
        return ''

    def clean_first_name(self):
        value = self.cleaned_data['first_name']
        validate_no_spam(value, 'El nombre')
        return value

    def clean_last_name(self):
        value = self.cleaned_data['last_name']
        validate_no_spam(value, 'El apellido')
        return value

    def clean_profession(self):
        value = self.cleaned_data['profession']
        validate_no_spam(value, 'La profesión')
        return value

    def clean_email(self):
        return validate_email_domain(self.cleaned_data['email'])

    def clean_phone(self):
        value = self.cleaned_data.get('phone', '')
        if value and not re.match(r'^[\d\s\+\-\(\)]+$', value):
            raise ValidationError('El teléfono solo puede contener números, espacios, +, - y paréntesis.')
        return value

    def clean_contribution_statement(self):
        return self.cleaned_data.get('contribution_statement', '')
