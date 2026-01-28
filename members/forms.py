from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileEditForm(forms.ModelForm):
    """Form for members to edit their profile information."""

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'phone',
            'profession', 'current_job', 'institution',
            'linkedin_url', 'bio'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tu nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tu apellido'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: +57 300 123 4567'
            }),
            'profession': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Ingeniero Nuclear, Físico, Médico'
            }),
            'current_job': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Director de Investigación'
            }),
            'institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Universidad Nacional de Colombia'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/tu-perfil'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Cuéntanos sobre tu trayectoria profesional, experiencia en el sector nuclear y áreas de interés...'
            }),
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'phone': 'Teléfono',
            'profession': 'Profesión / Título',
            'current_job': 'Cargo Actual',
            'institution': 'Empresa / Institución',
            'linkedin_url': 'Perfil de LinkedIn',
            'bio': 'Biografía Profesional',
        }

    def clean_linkedin_url(self):
        url = self.cleaned_data.get('linkedin_url')
        if url and 'linkedin.com' not in url.lower():
            raise forms.ValidationError('Por favor ingresa una URL válida de LinkedIn.')
        return url
