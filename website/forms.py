from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    # Honeypot anti-spam: los bots lo llenan, los humanos no lo ven.
    website = forms.CharField(required=False, widget=forms.HiddenInput())

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
