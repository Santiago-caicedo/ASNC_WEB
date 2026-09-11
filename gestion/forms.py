from django import forms

from users.models import User

from .models import Comite, MiembroComite, Nota, Persona, Proyecto, Tarea


def _style(form):
    """Apply Bootstrap classes to every widget of a form."""
    for field in form.fields.values():
        w = field.widget
        if isinstance(w, forms.CheckboxInput):
            w.attrs.setdefault('class', 'form-check-input')
        elif isinstance(w, (forms.Select, forms.SelectMultiple)):
            w.attrs.setdefault('class', 'form-select')
        else:
            w.attrs.setdefault('class', 'form-control')
        if isinstance(w, forms.Textarea):
            w.attrs.setdefault('rows', 4)


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(*args, **kwargs)


class ComiteForm(forms.ModelForm):
    class Meta:
        model = Comite
        fields = ['name', 'description', 'icon', 'color', 'coordinator', 'is_active', 'order']
        widgets = {
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['coordinator'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        self.fields['coordinator'].label_from_instance = lambda u: f'{u.get_full_name() or u.email} ({u.email})'
        _style(self)


class PersonaForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = [
            'first_name', 'last_name', 'tipo', 'email', 'phone', 'organization',
            'position', 'linkedin_url', 'user', 'notes', 'is_active',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
        # Users already linked to another persona cannot be linked twice.
        taken = Persona.objects.exclude(pk=self.instance.pk).exclude(user=None).values_list('user_id', flat=True)
        self.fields['user'].queryset = qs.exclude(pk__in=taken)
        self.fields['user'].label_from_instance = lambda u: f'{u.get_full_name() or u.email} ({u.email})'
        _style(self)


class MiembroComiteForm(forms.ModelForm):
    class Meta:
        model = MiembroComite
        fields = ['persona', 'rol', 'joined_at', 'notes']
        widgets = {'joined_at': DateInput()}

    def __init__(self, *args, comite=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.comite = comite
        qs = Persona.objects.filter(is_active=True)
        if comite is not None:
            qs = qs.exclude(membresias__comite=comite)
        self.fields['persona'].queryset = qs
        self.fields['persona'].empty_label = 'Selecciona una persona…'
        _style(self)

    def clean_persona(self):
        persona = self.cleaned_data['persona']
        if self.comite and MiembroComite.objects.filter(comite=self.comite, persona=persona).exists():
            raise forms.ValidationError('Esta persona ya pertenece al comité.')
        return persona


class ProyectoForm(forms.ModelForm):
    class Meta:
        model = Proyecto
        fields = [
            'title', 'comite', 'responsable', 'estado', 'prioridad',
            'start_date', 'due_date', 'avance', 'description',
        ]
        widgets = {
            'start_date': DateInput(), 'due_date': DateInput(),
            'avance': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comite'].queryset = Comite.objects.filter(is_active=True)
        self.fields['responsable'].queryset = Persona.objects.filter(is_active=True)
        _style(self)

    def clean(self):
        data = super().clean()
        start, due = data.get('start_date'), data.get('due_date')
        if start and due and due < start:
            self.add_error('due_date', 'La fecha objetivo no puede ser anterior a la fecha de inicio.')
        return data


class TareaForm(forms.ModelForm):
    class Meta:
        model = Tarea
        fields = [
            'title', 'comite', 'proyecto', 'asignado_a', 'estado', 'prioridad',
            'due_date', 'description',
        ]
        widgets = {'due_date': DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comite'].queryset = Comite.objects.filter(is_active=True)
        self.fields['proyecto'].queryset = Proyecto.objects.exclude(
            estado__in=Proyecto.CLOSED_STATES
        ).select_related('comite').order_by('title')
        self.fields['proyecto'].label_from_instance = (
            lambda p: f'{p.title} · {p.comite}' if p.comite_id else p.title
        )
        self.fields['asignado_a'].queryset = Persona.objects.filter(is_active=True)
        _style(self)


class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Escribe una nota de seguimiento, acuerdo o novedad…',
            }),
        }
