import re

from django import forms
from django.core.exceptions import ValidationError

from config.antispam import validate_email_domain, validate_no_spam

from .models import Inscripcion, Simposio


class InscripcionForm(forms.ModelForm):
    """Public registration form (with the same anti-bot layers as admissions)."""

    # Honeypot - bots fill this, humans don't see it
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    # Signed timestamp for the speed check (injected by the view)
    form_token = forms.CharField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Inscripcion
        fields = [
            'first_name', 'last_name', 'modality',
            'email', 'phone', 'attendee_type', 'institution', 'position', 'city',
            'accepts_data_policy',
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'autocomplete': 'given-name'}),
            'last_name': forms.TextInput(attrs={'autocomplete': 'family-name'}),
            'modality': forms.RadioSelect,
            'email': forms.EmailInput(attrs={'autocomplete': 'email', 'placeholder': 'tu@correo.com'}),
            'phone': forms.TextInput(attrs={'autocomplete': 'tel', 'placeholder': '+57 300 123 4567'}),
            'institution': forms.TextInput(attrs={'autocomplete': 'organization'}),
        }
        help_texts = {
            'first_name': 'Como deben aparecer en tu certificado.',
            'email': 'Aquí te enviaremos la confirmación de tu inscripción.',
        }
        labels = {
            'modality': '¿Cómo vas a participar?',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ('website', 'form_token'):
                continue
            if isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'
        self.fields['accepts_data_policy'].required = True
        self.fields['accepts_data_policy'].error_messages['required'] = (
            'Debes aceptar el tratamiento de datos para inscribirte.'
        )

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise ValidationError('Error en el formulario.')
        return ''

    def clean_first_name(self):
        return validate_no_spam(self.cleaned_data['first_name'].strip(), 'El nombre')

    def clean_last_name(self):
        return validate_no_spam(self.cleaned_data['last_name'].strip(), 'El apellido')

    def clean_email(self):
        return validate_email_domain(self.cleaned_data['email'].strip().lower())

    def clean_phone(self):
        value = self.cleaned_data.get('phone', '')
        if value and not re.match(r'^[\d\s\+\-\(\)]+$', value):
            raise ValidationError('El teléfono solo puede contener números, espacios, +, - y paréntesis.')
        return value

    def clean_institution(self):
        return validate_no_spam(self.cleaned_data.get('institution', ''), 'La institución')

    def clean_position(self):
        return validate_no_spam(self.cleaned_data.get('position', ''), 'La profesión o cargo')

    def clean_city(self):
        return validate_no_spam(self.cleaned_data.get('city', ''), 'La ciudad')


class SimposioForm(forms.ModelForm):
    """Everything the committee can change about the edition, from the portal."""

    class Meta:
        model = Simposio
        fields = [
            'title', 'hero_kicker', 'hero_title', 'tagline', 'description',
            'starts_on', 'ends_on', 'schedule_text',
            'venue', 'address', 'city',
            'agenda',
            'capacity', 'is_published', 'registration_open',
            'certificates_enabled', 'certificate_min_days', 'certificate_hours',
            'signer_name', 'signer_role',
        ]
        widgets = {
            'starts_on': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'ends_on': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 6}),
            'agenda': forms.Textarea(attrs={
                'rows': 10,
                'placeholder': 'Día 1\n8:00 a. m. | Registro y acreditación |\n9:00 a. m. | Conferencia inaugural | Nombre del ponente',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('starts_on'), cleaned.get('ends_on')
        if end and not start:
            self.add_error('starts_on', 'Indica el primer día.')
        if start and end and end < start:
            self.add_error('ends_on', 'El último día no puede ser anterior al primero.')
        if cleaned.get('registration_open') and not cleaned.get('is_published'):
            self.add_error(
                'registration_open',
                'Publica la página antes de abrir las inscripciones.',
            )
        return cleaned
