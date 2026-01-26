from django import forms
from .models import MemberCard


class PhotoUploadForm(forms.Form):
    """Form for associates to upload their photo via secure link."""

    photo = forms.ImageField(
        label='Foto para el carné',
        widget=forms.FileInput(attrs={
            'class': 'form-control form-control-lg',
            'accept': 'image/*'
        }),
        help_text='Sube una foto tipo documento (fondo claro, rostro visible, formato JPG o PNG)'
    )

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            # Validate file size (max 5MB)
            if photo.size > 5 * 1024 * 1024:
                raise forms.ValidationError(
                    'La imagen es demasiado grande. El tamaño máximo es 5MB.'
                )

            # Validate content type
            content_type = photo.content_type
            if content_type not in ['image/jpeg', 'image/png', 'image/jpg']:
                raise forms.ValidationError(
                    'Solo se permiten imágenes en formato JPG o PNG.'
                )

        return photo


class GenerateCardForm(forms.Form):
    """Form for admin to initiate card generation."""

    category = forms.ChoiceField(
        label='Categoría de membresía',
        choices=MemberCard.Category.choices,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial=MemberCard.Category.ASSOCIATE
    )

    send_email = forms.BooleanField(
        label='Enviar correo al asociado solicitando foto',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class CardSuspendForm(forms.Form):
    """Form for suspending a member card."""

    reason = forms.CharField(
        label='Motivo de suspensión',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Indique el motivo de la suspensión del carné...'
        }),
        required=True
    )


class CardRenewForm(forms.Form):
    """Form for renewing a member card."""

    new_expiry_year = forms.IntegerField(
        label='Año de vencimiento',
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 2026
        }),
        help_text='El carné vencerá el 31 de diciembre del año seleccionado'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone
        current_year = timezone.now().year
        self.fields['new_expiry_year'].initial = current_year + 1
        self.fields['new_expiry_year'].widget.attrs['min'] = current_year
