from django import forms
from django.core.exceptions import ValidationError

from .models import Convocatoria, ConvocatoriaField


INPUT_CLASS = 'form-control form-control-lg'
SELECT_CLASS = 'form-select form-select-lg'
CHECK_CLASS = 'form-check-input'


class ConvocatoriaForm(forms.ModelForm):
    """Admin form to create/edit the convocatoria metadata."""

    class Meta:
        model = Convocatoria
        fields = [
            'title',
            'description',
            'cover_image',
            'is_active',
            'opens_at',
            'closes_at',
            'success_message',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'cover_image': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'opens_at': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'closes_at': forms.DateTimeInput(
                attrs={'class': 'form-control', 'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M',
            ),
            'success_message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in ('opens_at', 'closes_at'):
            self.fields[f].input_formats = ['%Y-%m-%dT%H:%M']


class ConvocatoriaFieldForm(forms.ModelForm):
    """Admin form to create/edit a dynamic field."""

    class Meta:
        model = ConvocatoriaField
        fields = ['label', 'field_type', 'required', 'help_text', 'placeholder', 'options', 'order']
        widgets = {
            'label': forms.TextInput(attrs={'class': 'form-control'}),
            'field_type': forms.Select(attrs={'class': 'form-select'}),
            'required': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'help_text': forms.TextInput(attrs={'class': 'form-control'}),
            'placeholder': forms.TextInput(attrs={'class': 'form-control'}),
            'options': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Una opción por línea',
            }),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned = super().clean()
        field_type = cleaned.get('field_type')
        options = (cleaned.get('options') or '').strip()
        if field_type == ConvocatoriaField.FieldType.SELECT and not options:
            self.add_error('options', 'Debes proporcionar al menos una opción (una por línea).')
        return cleaned


# ============================================================================
# Dynamic submission form
# ============================================================================


def _build_django_field(field):
    """Return a concrete Django form Field from a ConvocatoriaField instance."""
    FT = ConvocatoriaField.FieldType
    common = {
        'label': field.label,
        'required': field.required,
        'help_text': field.help_text or '',
    }
    widget_attrs = {}
    if field.placeholder:
        widget_attrs['placeholder'] = field.placeholder

    ftype = field.field_type
    if ftype == FT.TEXT:
        widget_attrs['class'] = INPUT_CLASS
        return forms.CharField(max_length=255, widget=forms.TextInput(attrs=widget_attrs), **common)
    if ftype == FT.TEXTAREA:
        widget_attrs['class'] = INPUT_CLASS
        widget_attrs['rows'] = 4
        return forms.CharField(widget=forms.Textarea(attrs=widget_attrs), **common)
    if ftype == FT.EMAIL:
        widget_attrs['class'] = INPUT_CLASS
        widget_attrs['inputmode'] = 'email'
        widget_attrs['autocomplete'] = 'email'
        return forms.EmailField(widget=forms.EmailInput(attrs=widget_attrs), **common)
    if ftype == FT.PHONE:
        widget_attrs['class'] = INPUT_CLASS
        widget_attrs['inputmode'] = 'tel'
        widget_attrs['autocomplete'] = 'tel'
        return forms.CharField(max_length=30, widget=forms.TextInput(attrs=widget_attrs), **common)
    if ftype == FT.NUMBER:
        widget_attrs['class'] = INPUT_CLASS
        widget_attrs['inputmode'] = 'numeric'
        return forms.IntegerField(widget=forms.NumberInput(attrs=widget_attrs), **common)
    if ftype == FT.DATE:
        widget_attrs['class'] = INPUT_CLASS
        widget_attrs['type'] = 'date'
        return forms.DateField(widget=forms.DateInput(attrs=widget_attrs), **common)
    if ftype == FT.SELECT:
        choices = [('', '— Selecciona —')] + [(opt, opt) for opt in field.options_list]
        return forms.ChoiceField(choices=choices, widget=forms.Select(attrs={'class': SELECT_CLASS}), **common)
    if ftype == FT.CHECKBOX:
        return forms.BooleanField(widget=forms.CheckboxInput(attrs={'class': CHECK_CLASS}), **common)
    if ftype == FT.FILE:
        widget_attrs['class'] = 'form-control form-control-lg'
        return forms.FileField(widget=forms.ClearableFileInput(attrs=widget_attrs), **common)

    raise ValidationError(f'Tipo de campo desconocido: {ftype}')


class SubmissionForm(forms.Form):
    """Dynamic form built at runtime from a Convocatoria's fields."""

    def __init__(self, *args, convocatoria=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.convocatoria = convocatoria
        if convocatoria is None:
            return
        for field in convocatoria.fields.all():
            self.fields[field.input_name] = _build_django_field(field)
            self.fields[field.input_name].convocatoria_field = field

    def iter_rendered_fields(self):
        """Yield (convocatoria_field, bound_form_field) pairs ordered by form order."""
        for name, bf in self.fields.items():
            yield getattr(bf, 'convocatoria_field', None), self[name]
