from django import forms
from django.contrib.auth import get_user_model
from website.models import FeaturedMember, NewsArticle
from admissions.models import MembershipApplication

User = get_user_model()


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


class NewsArticleForm(forms.ModelForm):
    class Meta:
        model = NewsArticle
        fields = [
            'title', 'cover_image', 'excerpt', 'content', 'is_published'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Título de la noticia'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Resumen corto que aparecerá en el listado de noticias...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 15,
                'placeholder': 'Contenido completo de la noticia...'
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class EmailComposeForm(forms.Form):
    """Formulario para componer y enviar correos masivos"""

    RECIPIENT_CHOICES = [
        ('manual', 'Ingresar correos manualmente'),
        ('users', 'Usuarios del sistema'),
        ('applicants', 'Solicitantes de membresía'),
    ]

    recipient_type = forms.ChoiceField(
        label='Tipo de destinatarios',
        choices=RECIPIENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='manual'
    )

    manual_emails = forms.CharField(
        label='Correos electrónicos',
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Ingresa los correos separados por coma o salto de línea\nEj: correo1@ejemplo.com, correo2@ejemplo.com'
        }),
        help_text='Separa los correos con coma (,) o salto de línea'
    )

    selected_users = forms.ModelMultipleChoiceField(
        label='Seleccionar usuarios',
        queryset=User.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    selected_applicants = forms.ModelMultipleChoiceField(
        label='Seleccionar solicitantes',
        queryset=MembershipApplication.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    subject = forms.CharField(
        label='Asunto',
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Asunto del correo'
        })
    )

    message = forms.CharField(
        label='Mensaje',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 10,
            'placeholder': 'Escribe el contenido del correo aquí...'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        recipient_type = cleaned_data.get('recipient_type')
        manual_emails = cleaned_data.get('manual_emails', '')
        selected_users = cleaned_data.get('selected_users')
        selected_applicants = cleaned_data.get('selected_applicants')

        if recipient_type == 'manual':
            if not manual_emails.strip():
                raise forms.ValidationError('Debes ingresar al menos un correo electrónico.')
        elif recipient_type == 'users':
            if not selected_users:
                raise forms.ValidationError('Debes seleccionar al menos un usuario.')
        elif recipient_type == 'applicants':
            if not selected_applicants:
                raise forms.ValidationError('Debes seleccionar al menos un solicitante.')

        return cleaned_data

    def get_recipients(self):
        """Retorna lista de correos según la selección"""
        recipient_type = self.cleaned_data.get('recipient_type')
        emails = []

        if recipient_type == 'manual':
            raw_emails = self.cleaned_data.get('manual_emails', '')
            raw_emails = raw_emails.replace('\n', ',').replace('\r', '')
            emails = [e.strip() for e in raw_emails.split(',') if e.strip()]

        elif recipient_type == 'users':
            users = self.cleaned_data.get('selected_users', [])
            emails = [user.email for user in users if user.email]

        elif recipient_type == 'applicants':
            applicants = self.cleaned_data.get('selected_applicants', [])
            emails = [app.email for app in applicants if app.email]

        return list(set(emails))
