"""Internal CRM views (committees, people, projects, tasks, notes).

Every view is gated by ``SuperuserRequiredMixin`` / ``superuser_required``:
for now this module is only visible to superadmins.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView,
)

from admissions.views import SuperuserRequiredMixin
from users.models import User

from .forms import (
    ComiteForm, MiembroComiteForm, NotaForm, PersonaForm, ProyectoForm, TareaForm,
)
from .models import Comite, MiembroComite, Nota, Persona, Prioridad, Proyecto, Tarea


def superuser_required(view_func):
    """Function-view counterpart of ``SuperuserRequiredMixin``."""
    return login_required(login_url='/acceso/')(
        user_passes_test(lambda u: u.is_superuser, login_url='/acceso/')(view_func)
    )


def _safe_next(request, fallback):
    """Return the ``next`` param only when it is a local path."""
    nxt = request.POST.get('next') or request.GET.get('next')
    if nxt and nxt.startswith('/') and not nxt.startswith('//'):
        return nxt
    return fallback


# ============================================================================
# Panel
# ============================================================================


class GestionHomeView(SuperuserRequiredMixin, TemplateView):
    template_name = 'gestion/home.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = timezone.localdate()
        open_tasks = Tarea.objects.exclude(estado__in=Tarea.CLOSED_STATES)

        ctx['comites'] = (
            Comite.objects.filter(is_active=True)
            .annotate(
                n_miembros=Count('miembros', filter=Q(miembros__is_active=True), distinct=True),
                n_proyectos=Count('proyectos', filter=Q(proyectos__estado__in=Proyecto.ACTIVE_STATES), distinct=True),
                n_tareas=Count('tareas', filter=~Q(tareas__estado__in=Tarea.CLOSED_STATES), distinct=True),
                n_vencidas=Count(
                    'tareas',
                    filter=~Q(tareas__estado__in=Tarea.CLOSED_STATES) & Q(tareas__due_date__lt=today),
                    distinct=True,
                ),
            )
            .order_by('order', 'name')
        )
        ctx['personas_count'] = Persona.objects.filter(is_active=True).count()
        ctx['proyectos_activos'] = Proyecto.objects.filter(estado__in=Proyecto.ACTIVE_STATES).count()
        ctx['tareas_abiertas'] = open_tasks.count()
        ctx['tareas_vencidas'] = open_tasks.filter(due_date__lt=today).count()
        ctx['proximas'] = (
            open_tasks.filter(due_date__isnull=False)
            .select_related('comite', 'proyecto', 'asignado_a')
            .order_by('due_date')[:8]
        )
        ctx['sin_fecha'] = open_tasks.filter(due_date__isnull=True).count()
        ctx['proyectos_recientes'] = (
            Proyecto.objects.exclude(estado__in=Proyecto.CLOSED_STATES)
            .select_related('comite', 'responsable').order_by('-updated_at')[:6]
        )
        ctx['notas_recientes'] = (
            Nota.objects.select_related('author', 'comite', 'persona', 'proyecto', 'tarea')
            .order_by('-created_at')[:8]
        )
        return ctx


# ============================================================================
# Comités
# ============================================================================


class ComiteListView(SuperuserRequiredMixin, ListView):
    model = Comite
    template_name = 'gestion/comites/list.html'
    context_object_name = 'comites'

    def get_queryset(self):
        today = timezone.localdate()
        return Comite.objects.annotate(
            n_miembros=Count('miembros', filter=Q(miembros__is_active=True), distinct=True),
            n_proyectos=Count('proyectos', filter=Q(proyectos__estado__in=Proyecto.ACTIVE_STATES), distinct=True),
            n_tareas=Count('tareas', filter=~Q(tareas__estado__in=Tarea.CLOSED_STATES), distinct=True),
            n_vencidas=Count(
                'tareas',
                filter=~Q(tareas__estado__in=Tarea.CLOSED_STATES) & Q(tareas__due_date__lt=today),
                distinct=True,
            ),
        ).select_related('coordinator').order_by('order', 'name')


class ComiteDetailView(SuperuserRequiredMixin, DetailView):
    model = Comite
    template_name = 'gestion/comites/detail.html'
    context_object_name = 'comite'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        c = self.object
        ctx['miembros'] = c.miembros.select_related('persona', 'persona__user').order_by('-is_active', 'rol', 'persona__first_name')
        ctx['member_form'] = MiembroComiteForm(comite=c)
        ctx['roles'] = MiembroComite.Rol.choices
        ctx['proyectos'] = c.proyectos.select_related('responsable').order_by('estado', '-updated_at')
        ctx['tareas'] = (
            c.tareas.exclude(estado__in=Tarea.CLOSED_STATES)
            .select_related('proyecto', 'asignado_a').order_by('due_date', '-prioridad')
        )
        ctx['tareas_cerradas_count'] = c.tareas.filter(estado__in=Tarea.CLOSED_STATES).count()
        ctx['notas'] = c.notas.select_related('author')
        ctx['nota_form'] = NotaForm()
        ctx['nota_kind'] = 'comite'
        return ctx


class ComiteCreateView(SuperuserRequiredMixin, CreateView):
    model = Comite
    form_class = ComiteForm
    template_name = 'gestion/form.html'
    extra_context = {'page_title': 'Nuevo comité', 'back_url_name': 'gestion:comite_list'}

    def form_valid(self, form):
        messages.success(self.request, 'Comité creado exitosamente.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('gestion:comite_detail', args=[self.object.pk])


class ComiteUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Comite
    form_class = ComiteForm
    template_name = 'gestion/form.html'
    extra_context = {'page_title': 'Editar comité'}

    def form_valid(self, form):
        messages.success(self.request, 'Comité actualizado.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('gestion:comite_detail', args=[self.object.pk])


class ComiteDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Comite
    template_name = 'gestion/confirm_delete.html'
    success_url = reverse_lazy('gestion:comite_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Eliminar comité'
        ctx['object_label'] = self.object.name
        ctx['warning'] = (
            f'Se quitarán {self.object.miembros.count()} membresías y las notas del comité. '
            'Los proyectos y tareas quedarán sin comité asignado (no se borran).'
        )
        ctx['cancel_url'] = reverse('gestion:comite_detail', args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Comité eliminado.')
        return super().form_valid(form)


@superuser_required
@require_POST
def add_member(request, pk):
    comite = get_object_or_404(Comite, pk=pk)
    form = MiembroComiteForm(request.POST, comite=comite)
    if form.is_valid():
        miembro = form.save(commit=False)
        miembro.comite = comite
        miembro.save()
        messages.success(request, f'{miembro.persona} se agregó al comité como {miembro.get_rol_display()}.')
    else:
        for errors in form.errors.values():
            messages.error(request, errors[0])
    return redirect('gestion:comite_detail', pk=pk)


@superuser_required
@require_POST
def update_member(request, pk):
    miembro = get_object_or_404(MiembroComite.objects.select_related('comite', 'persona'), pk=pk)
    rol = request.POST.get('rol')
    if rol in MiembroComite.Rol.values:
        miembro.rol = rol
    if 'is_active' in request.POST:
        miembro.is_active = request.POST.get('is_active') == '1'
    miembro.save()
    messages.success(request, f'Membresía de {miembro.persona} actualizada.')
    return redirect('gestion:comite_detail', pk=miembro.comite_id)


@superuser_required
@require_POST
def remove_member(request, pk):
    miembro = get_object_or_404(MiembroComite.objects.select_related('comite', 'persona'), pk=pk)
    comite_id = miembro.comite_id
    nombre = str(miembro.persona)
    miembro.delete()
    messages.success(request, f'{nombre} se quitó del comité.')
    return redirect(_safe_next(request, reverse('gestion:comite_detail', args=[comite_id])))


# ============================================================================
# Personas
# ============================================================================


class PersonaListView(SuperuserRequiredMixin, ListView):
    model = Persona
    template_name = 'gestion/personas/list.html'
    context_object_name = 'personas'
    paginate_by = 25

    def get_queryset(self):
        qs = Persona.objects.select_related('user').prefetch_related('membresias__comite').annotate(
            n_tareas=Count('tareas_asignadas', filter=~Q(tareas_asignadas__estado__in=Tarea.CLOSED_STATES), distinct=True),
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
                | Q(organization__icontains=q) | Q(position__icontains=q)
            )
        tipo = self.request.GET.get('tipo')
        if tipo in Persona.Tipo.values:
            qs = qs.filter(tipo=tipo)
        comite = self.request.GET.get('comite')
        if comite and comite.isdigit():
            qs = qs.filter(membresias__comite_id=int(comite), membresias__is_active=True)
        estado = self.request.GET.get('estado', 'activas')
        if estado == 'activas':
            qs = qs.filter(is_active=True)
        elif estado == 'inactivas':
            qs = qs.filter(is_active=False)
        # Meta.ordering is dropped on aggregated querysets; make it explicit.
        return qs.distinct().order_by('first_name', 'last_name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['comites'] = Comite.objects.filter(is_active=True)
        ctx['tipos'] = Persona.Tipo.choices
        ctx['filters'] = {
            'q': self.request.GET.get('q', ''),
            'tipo': self.request.GET.get('tipo', ''),
            'comite': self.request.GET.get('comite', ''),
            'estado': self.request.GET.get('estado', 'activas'),
        }
        ctx['total_personas'] = Persona.objects.filter(is_active=True).count()
        ctx['sin_importar'] = (
            User.objects.filter(is_active=True, persona_crm__isnull=True)
            .exclude(role=User.Role.ADMIN).exclude(is_superuser=True).count()
        )
        return ctx


class PersonaDetailView(SuperuserRequiredMixin, DetailView):
    model = Persona
    template_name = 'gestion/personas/detail.html'
    context_object_name = 'persona'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p = self.object
        ctx['membresias'] = p.membresias.select_related('comite')
        ctx['tareas'] = p.tareas_asignadas.select_related('comite', 'proyecto').order_by('estado', 'due_date')
        ctx['proyectos'] = p.proyectos_liderados.select_related('comite')
        ctx['notas'] = p.notas.select_related('author')
        ctx['nota_form'] = NotaForm()
        ctx['nota_kind'] = 'persona'
        return ctx


class PersonaCreateView(SuperuserRequiredMixin, CreateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'gestion/form.html'
    extra_context = {'page_title': 'Nueva persona', 'back_url_name': 'gestion:persona_list'}

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Persona registrada en el CRM.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('gestion:persona_detail', args=[self.object.pk])


class PersonaUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Persona
    form_class = PersonaForm
    template_name = 'gestion/form.html'
    extra_context = {'page_title': 'Editar persona'}

    def form_valid(self, form):
        messages.success(self.request, 'Persona actualizada.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('gestion:persona_detail', args=[self.object.pk])


class PersonaDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Persona
    template_name = 'gestion/confirm_delete.html'
    success_url = reverse_lazy('gestion:persona_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Eliminar persona'
        ctx['object_label'] = self.object.full_name
        ctx['warning'] = (
            'Se quitará de todos los comités y se borrarán sus notas. '
            'Las tareas que tenía asignadas quedarán sin responsable. '
            'La cuenta de usuario de la plataforma (si existe) NO se elimina.'
        )
        ctx['cancel_url'] = reverse('gestion:persona_detail', args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Persona eliminada del CRM.')
        return super().form_valid(form)


@superuser_required
@require_POST
def import_users(request):
    """Create a Persona for every active associate that does not have one yet."""
    users = (
        User.objects.filter(is_active=True, persona_crm__isnull=True)
        .exclude(role=User.Role.ADMIN).exclude(is_superuser=True)
    )
    created = 0
    for user in users:
        _, was_created = Persona.from_user(user, created_by=request.user)
        created += int(was_created)
    if created:
        messages.success(request, f'Se importaron {created} asociados al CRM.')
    else:
        messages.info(request, 'Todos los asociados ya están registrados en el CRM.')
    return redirect('gestion:persona_list')


# ============================================================================
# Proyectos
# ============================================================================


class ProyectoListView(SuperuserRequiredMixin, ListView):
    model = Proyecto
    template_name = 'gestion/proyectos/list.html'
    context_object_name = 'proyectos'
    paginate_by = 20

    def get_queryset(self):
        qs = Proyecto.objects.select_related('comite', 'responsable').annotate(
            n_tareas=Count('tareas', filter=~Q(tareas__estado=Tarea.Estado.CANCELADA), distinct=True),
            n_hechas=Count('tareas', filter=Q(tareas__estado=Tarea.Estado.COMPLETADA), distinct=True),
        )
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        comite = self.request.GET.get('comite')
        if comite and comite.isdigit():
            qs = qs.filter(comite_id=int(comite))
        elif comite == 'transversal':
            qs = qs.filter(comite__isnull=True)
        estado = self.request.GET.get('estado', 'abiertos')
        if estado == 'abiertos':
            qs = qs.exclude(estado__in=Proyecto.CLOSED_STATES)
        elif estado in Proyecto.Estado.values:
            qs = qs.filter(estado=estado)
        return qs.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['comites'] = Comite.objects.filter(is_active=True)
        ctx['estados'] = Proyecto.Estado.choices
        ctx['filters'] = {
            'q': self.request.GET.get('q', ''),
            'comite': self.request.GET.get('comite', ''),
            'estado': self.request.GET.get('estado', 'abiertos'),
        }
        return ctx


class ProyectoDetailView(SuperuserRequiredMixin, DetailView):
    model = Proyecto
    template_name = 'gestion/proyectos/detail.html'
    context_object_name = 'proyecto'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p = self.object
        tareas = list(p.tareas.select_related('asignado_a').order_by('due_date', '-prioridad'))
        ctx['columnas'] = [
            (estado, label, [t for t in tareas if t.estado == estado])
            for estado, label in Tarea.Estado.choices if estado in Tarea.BOARD_STATES
        ]
        ctx['canceladas'] = [t for t in tareas if t.estado == Tarea.Estado.CANCELADA]
        ctx['estados_proyecto'] = Proyecto.Estado.choices
        ctx['notas'] = p.notas.select_related('author')
        ctx['nota_form'] = NotaForm()
        ctx['nota_kind'] = 'proyecto'
        return ctx


class ProyectoCreateView(SuperuserRequiredMixin, CreateView):
    model = Proyecto
    form_class = ProyectoForm
    template_name = 'gestion/form.html'
    extra_context = {'page_title': 'Nuevo proyecto', 'back_url_name': 'gestion:proyecto_list'}

    def get_initial(self):
        initial = super().get_initial()
        comite = self.request.GET.get('comite')
        if comite and comite.isdigit():
            initial['comite'] = int(comite)
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Proyecto creado.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('gestion:proyecto_detail', args=[self.object.pk])


class ProyectoUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Proyecto
    form_class = ProyectoForm
    template_name = 'gestion/form.html'
    extra_context = {'page_title': 'Editar proyecto'}

    def form_valid(self, form):
        messages.success(self.request, 'Proyecto actualizado.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('gestion:proyecto_detail', args=[self.object.pk])


class ProyectoDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Proyecto
    template_name = 'gestion/confirm_delete.html'
    success_url = reverse_lazy('gestion:proyecto_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Eliminar proyecto'
        ctx['object_label'] = self.object.title
        ctx['warning'] = (
            f'Se borrarán también sus {self.object.tareas.count()} tareas y todas las notas asociadas. '
            'Esta acción no se puede deshacer.'
        )
        ctx['cancel_url'] = reverse('gestion:proyecto_detail', args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Proyecto eliminado.')
        return super().form_valid(form)


@superuser_required
@require_POST
def change_project_status(request, pk, estado):
    proyecto = get_object_or_404(Proyecto, pk=pk)
    if estado not in Proyecto.Estado.values:
        messages.error(request, 'Estado no válido.')
    else:
        proyecto.estado = estado
        proyecto.save(update_fields=['estado', 'updated_at'])
        messages.success(request, f'Proyecto marcado como "{proyecto.get_estado_display()}".')
    return redirect(_safe_next(request, reverse('gestion:proyecto_detail', args=[pk])))


# ============================================================================
# Tareas
# ============================================================================


class TareaFilterMixin:
    """Shared GET filters for the task list and the board."""

    def filtered_tasks(self):
        qs = Tarea.objects.select_related('comite', 'proyecto', 'asignado_a')
        g = self.request.GET
        q = g.get('q', '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
        comite = g.get('comite')
        if comite and comite.isdigit():
            qs = qs.filter(comite_id=int(comite))
        proyecto = g.get('proyecto')
        if proyecto and proyecto.isdigit():
            qs = qs.filter(proyecto_id=int(proyecto))
        persona = g.get('persona')
        if persona and persona.isdigit():
            qs = qs.filter(asignado_a_id=int(persona))
        elif persona == 'nadie':
            qs = qs.filter(asignado_a__isnull=True)
        prioridad = g.get('prioridad')
        if prioridad in Prioridad.values:
            qs = qs.filter(prioridad=prioridad)
        return qs

    def filter_context(self):
        g = self.request.GET
        return {
            'comites': Comite.objects.filter(is_active=True),
            'proyectos_filtro': Proyecto.objects.exclude(estado__in=Proyecto.CLOSED_STATES).order_by('title'),
            'personas_filtro': Persona.objects.filter(is_active=True),
            'prioridades': Prioridad.choices,
            'estados': Tarea.Estado.choices,
            'filters': {
                'q': g.get('q', ''),
                'comite': g.get('comite', ''),
                'proyecto': g.get('proyecto', ''),
                'persona': g.get('persona', ''),
                'prioridad': g.get('prioridad', ''),
                'estado': g.get('estado', 'abiertas'),
            },
            'querystring': g.urlencode(),
        }


class TareaListView(SuperuserRequiredMixin, TareaFilterMixin, ListView):
    model = Tarea
    template_name = 'gestion/tareas/list.html'
    context_object_name = 'tareas'
    paginate_by = 30

    def get_queryset(self):
        qs = self.filtered_tasks()
        estado = self.request.GET.get('estado', 'abiertas')
        if estado == 'abiertas':
            qs = qs.exclude(estado__in=Tarea.CLOSED_STATES)
        elif estado == 'vencidas':
            qs = qs.exclude(estado__in=Tarea.CLOSED_STATES).filter(due_date__lt=timezone.localdate())
        elif estado in Tarea.Estado.values:
            qs = qs.filter(estado=estado)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.filter_context())
        today = timezone.localdate()
        abiertas = Tarea.objects.exclude(estado__in=Tarea.CLOSED_STATES)
        ctx['kpi'] = {
            'abiertas': abiertas.count(),
            'vencidas': abiertas.filter(due_date__lt=today).count(),
            'semana': abiertas.filter(due_date__gte=today, due_date__lte=today + timezone.timedelta(days=7)).count(),
            'completadas': Tarea.objects.filter(estado=Tarea.Estado.COMPLETADA).count(),
        }
        return ctx


class TareaBoardView(SuperuserRequiredMixin, TareaFilterMixin, TemplateView):
    template_name = 'gestion/tareas/board.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(self.filter_context())
        tareas = list(self.filtered_tasks().exclude(estado=Tarea.Estado.CANCELADA).order_by('due_date', '-prioridad'))
        ctx['columnas'] = [
            (estado, label, [t for t in tareas if t.estado == estado])
            for estado, label in Tarea.Estado.choices if estado in Tarea.BOARD_STATES
        ]
        return ctx


class TareaDetailView(SuperuserRequiredMixin, DetailView):
    model = Tarea
    template_name = 'gestion/tareas/detail.html'
    context_object_name = 'tarea'
    queryset = Tarea.objects.select_related('comite', 'proyecto', 'asignado_a', 'created_by')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['estados'] = Tarea.Estado.choices
        ctx['notas'] = self.object.notas.select_related('author')
        ctx['nota_form'] = NotaForm()
        ctx['nota_kind'] = 'tarea'
        return ctx


class TareaCreateView(SuperuserRequiredMixin, CreateView):
    model = Tarea
    form_class = TareaForm
    template_name = 'gestion/form.html'
    extra_context = {'page_title': 'Nueva tarea', 'back_url_name': 'gestion:tarea_list'}

    def get_initial(self):
        initial = super().get_initial()
        g = self.request.GET
        for key in ('comite', 'proyecto'):
            val = g.get(key)
            if val and val.isdigit():
                initial[key] = int(val)
        persona = g.get('persona')
        if persona and persona.isdigit():
            initial['asignado_a'] = int(persona)
        if 'proyecto' in initial and 'comite' not in initial:
            proyecto = Proyecto.objects.filter(pk=initial['proyecto']).first()
            if proyecto and proyecto.comite_id:
                initial['comite'] = proyecto.comite_id
        return initial

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Tarea creada.')
        return super().form_valid(form)

    def get_success_url(self):
        nxt = _safe_next(self.request, '')
        return nxt or reverse('gestion:tarea_detail', args=[self.object.pk])


class TareaUpdateView(SuperuserRequiredMixin, UpdateView):
    model = Tarea
    form_class = TareaForm
    template_name = 'gestion/form.html'
    extra_context = {'page_title': 'Editar tarea'}

    def form_valid(self, form):
        messages.success(self.request, 'Tarea actualizada.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('gestion:tarea_detail', args=[self.object.pk])


class TareaDeleteView(SuperuserRequiredMixin, DeleteView):
    model = Tarea
    template_name = 'gestion/confirm_delete.html'
    success_url = reverse_lazy('gestion:tarea_list')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = 'Eliminar tarea'
        ctx['object_label'] = self.object.title
        ctx['warning'] = 'Se borrarán también sus notas de seguimiento. Esta acción no se puede deshacer.'
        ctx['cancel_url'] = reverse('gestion:tarea_detail', args=[self.object.pk])
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Tarea eliminada.')
        return super().form_valid(form)


@superuser_required
@require_POST
def change_task_status(request, pk, estado):
    tarea = get_object_or_404(Tarea, pk=pk)
    if estado not in Tarea.Estado.values:
        messages.error(request, 'Estado no válido.')
    else:
        tarea.estado = estado
        tarea.save()
        messages.success(request, f'"{tarea.title}" → {tarea.get_estado_display()}.')
    return redirect(_safe_next(request, reverse('gestion:tarea_detail', args=[pk])))


# ============================================================================
# Notas de seguimiento
# ============================================================================


NOTE_TARGETS = {
    'comite': (Comite, 'comite', 'gestion:comite_detail'),
    'persona': (Persona, 'persona', 'gestion:persona_detail'),
    'proyecto': (Proyecto, 'proyecto', 'gestion:proyecto_detail'),
    'tarea': (Tarea, 'tarea', 'gestion:tarea_detail'),
}


@superuser_required
@require_POST
def add_note(request, kind, pk):
    if kind not in NOTE_TARGETS:
        messages.error(request, 'Destino de la nota no válido.')
        return redirect('gestion:home')
    model, field, detail_url = NOTE_TARGETS[kind]
    target = get_object_or_404(model, pk=pk)
    form = NotaForm(request.POST)
    if form.is_valid():
        nota = form.save(commit=False)
        nota.author = request.user
        setattr(nota, field, target)
        nota.save()
        messages.success(request, 'Nota agregada.')
    else:
        messages.error(request, 'La nota no puede estar vacía.')
    return redirect(detail_url, pk=pk)


@superuser_required
@require_POST
def delete_note(request, pk):
    nota = get_object_or_404(Nota, pk=pk)
    fallback = reverse('gestion:home')
    for kind, (model, field, detail_url) in NOTE_TARGETS.items():
        obj_id = getattr(nota, f'{field}_id')
        if obj_id:
            fallback = reverse(detail_url, args=[obj_id])
            break
    nota.delete()
    messages.success(request, 'Nota eliminada.')
    return redirect(_safe_next(request, fallback))
