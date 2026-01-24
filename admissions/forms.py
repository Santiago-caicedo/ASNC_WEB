from django import forms
from .models import MembershipApplication

class MembershipApplicationForm(forms.ModelForm):
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
                'placeholder': 'Ej: Ingeniero Nuclear, Físico Médico',
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