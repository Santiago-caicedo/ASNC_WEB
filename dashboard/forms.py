from django import forms
from website.models import FeaturedMember


class FeaturedMemberForm(forms.ModelForm):
    class Meta:
        model = FeaturedMember
        fields = [
            'full_name', 'photo', 'association_position',
            'profession', 'professional_trajectory', 'linkedin_url',
            'is_active', 'display_order'
        ]
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre completo del asociado'
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'association_position': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Presidente, Director Científico'
            }),
            'profession': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ej: Ingeniero Nuclear, Físico Médico'
            }),
            'professional_trajectory': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describa la trayectoria profesional, logros y experiencia relevante...'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/...'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0
            }),
        }
