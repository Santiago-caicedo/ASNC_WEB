from django import forms

from users.models import User

from .models import Comite, MiembroComite, Nota, Proyecto, Tarea


def usuarios_activos():
    return User.objects.filter(is_active=True).order_by('first_name', 'last_name', 'email')


def nombre_usuario(u):
    return u.get_full_name() or u.email


class DateInput(forms.DateInput):
    input_type = 'date'

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('format', '%Y-%m-%d')
        super().__init__(*args, **kwargs)


class _Base(forms.ModelForm):
    """Clases de Bootstrap y nombres legibles de usuario en los selectores."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            w = field.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault('class', 'form-check-input')
            elif isinstance(w, forms.Select):
                w.attrs.setdefault('class', 'form-select')
            else:
                w.attrs.setdefault('class', 'form-control')
            if isinstance(w, forms.Textarea):
                w.attrs.setdefault('rows', 3)
            if isinstance(field, forms.ModelChoiceField) and field.queryset.model is User:
                field.queryset = usuarios_activos()
                field.label_from_instance = nombre_usuario
                field.empty_label = 'Sin asignar'


class ComiteForm(_Base):
    class Meta:
        model = Comite
        fields = ['name', 'description', 'coordinator', 'is_active', 'order']


class MiembroForm(_Base):
    class Meta:
        model = MiembroComite
        fields = ['user', 'rol']

    def __init__(self, *args, comite=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.comite = comite
        self.fields['user'].empty_label = 'Elige un usuario…'
        if comite is not None:
            self.fields['user'].queryset = usuarios_activos().exclude(membresias_comite__comite=comite)

    def clean_user(self):
        user = self.cleaned_data['user']
        if self.comite and MiembroComite.objects.filter(comite=self.comite, user=user).exists():
            raise forms.ValidationError('Ya es integrante de este comité.')
        return user


class ProyectoForm(_Base):
    class Meta:
        model = Proyecto
        fields = ['title', 'comite', 'responsable', 'estado', 'prioridad', 'start_date', 'due_date', 'description']
        widgets = {'start_date': DateInput(), 'due_date': DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comite'].queryset = Comite.objects.filter(is_active=True)
        self.fields['comite'].empty_label = 'Transversal (sin comité)'

    def clean(self):
        data = super().clean()
        if data.get('start_date') and data.get('due_date') and data['due_date'] < data['start_date']:
            self.add_error('due_date', 'La fecha objetivo no puede ser anterior al inicio.')
        return data


class TareaForm(_Base):
    class Meta:
        model = Tarea
        fields = ['title', 'comite', 'proyecto', 'asignado_a', 'estado', 'prioridad', 'due_date', 'description']
        widgets = {'due_date': DateInput()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comite'].queryset = Comite.objects.filter(is_active=True)
        self.fields['comite'].empty_label = 'Sin comité'
        self.fields['proyecto'].queryset = (
            Proyecto.objects.exclude(estado=Proyecto.Estado.CERRADO).select_related('comite').order_by('title')
        )
        self.fields['proyecto'].empty_label = 'Sin proyecto'
        self.fields['proyecto'].label_from_instance = (
            lambda p: f'{p.title} · {p.comite}' if p.comite_id else f'{p.title} · Transversal'
        )


class TareaRapidaForm(forms.Form):
    """Alta rápida desde la lista: título, responsable y fecha, nada más."""

    title = forms.CharField(max_length=200)
    asignado_a = forms.ModelChoiceField(queryset=User.objects.none(), required=False)
    due_date = forms.DateField(required=False, input_formats=['%Y-%m-%d'])
    proyecto = forms.ModelChoiceField(queryset=Proyecto.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['asignado_a'].queryset = usuarios_activos()


class NotaForm(forms.ModelForm):
    class Meta:
        model = Nota
        fields = ['content']
        widgets = {'content': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Escribe una nota…'})}
