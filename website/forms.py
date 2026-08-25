from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from config.antispam import (
    validate_email_domain, validate_free_text, validate_no_spam,
)

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    # Honeypot anti-spam: los bots lo llenan, los humanos no lo ven.
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    # Timestamp firmado para el control de velocidad (lo inyecta la vista)
    form_token = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Tu nombre'),
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'tu@email.com',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Asunto'),
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control form-control-lg',
                'rows': 5,
                'placeholder': _('Escribe tu mensaje aquí...'),
            }),
        }

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise ValidationError('Error en el formulario.')
        return ''

    def clean_name(self):
        return validate_no_spam(self.cleaned_data['name'], 'El nombre')

    def clean_subject(self):
        return validate_no_spam(self.cleaned_data['subject'], 'El asunto')

    def clean_message(self):
        # Un mensaje legítimo puede mencionar un dominio; una pared de enlaces no.
        return validate_free_text(self.cleaned_data['message'], 'El mensaje', max_links=1)

    def clean_email(self):
        return validate_email_domain(self.cleaned_data['email'])
