"""Gestión de comités en una sola pantalla.

``WorkspaceView`` dibuja todo: la lista de comités, y del comité elegido sus
integrantes, proyectos con tareas y notas. El resto son acciones POST que
guardan y vuelven a la misma pantalla. Acceso solo para superadministradores.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from admissions.views import SuperuserRequiredMixin

from .forms import (
    ComiteForm, MiembroForm, NotaForm, ProyectoForm, TareaForm, TareaRapidaForm, usuarios_activos,
)
from .models import Comite, MiembroComite, Nota, Proyecto, Tarea


def superuser_required(view_func):
    return login_required(login_url='/acceso/')(
        user_passes_test(lambda u: u.is_superuser, login_url='/acceso/')(view_func)
    )


def _volver(request, comite_id=None):
    """A la misma pantalla: ``next`` si es una ruta local, si no el comité dado."""
    nxt = request.POST.get('next') or request.GET.get('next')
    if nxt and nxt.startswith('/') and not nxt.startswith('//'):
        return redirect(nxt)
    url = reverse('gestion:workspace')
    return redirect(f'{url}?comite={comite_id}' if comite_id else url)


def _errores(request, form):
    for field, errs in form.errors.items():
        etiqueta = form.fields[field].label if field in form.fields else ''
        messages.error(request, f'{etiqueta}: {errs[0]}' if etiqueta else errs[0])


# ---------------------------------------------------------------------------
# Pantalla única
# ---------------------------------------------------------------------------


class WorkspaceView(SuperuserRequiredMixin, TemplateView):
    template_name = 'gestion/workspace.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        abiertas = ~Q(tareas__estado__in=Tarea.CLOSED_STATES)
        ctx['comites'] = (
            Comite.objects.select_related('coordinator')
            .annotate(
                abiertas=Count('tareas', filter=abiertas, distinct=True),
                vencidas=Count('tareas', filter=abiertas & Q(tareas__due_date__lt=hoy), distinct=True),
            )
            .order_by('-is_active', 'order', 'name')
        )
        ctx['hoy'] = hoy
        ctx['mostrar_todas'] = self.request.GET.get('todas') == '1'
        ctx['usuarios'] = usuarios_activos()
        ctx['comite_form'] = ComiteForm()
        ctx['proyecto_form'] = ProyectoForm()
        ctx['tarea_form'] = TareaForm()
        ctx['nota_form'] = NotaForm()
        ctx['estados_tarea'] = Tarea.Estado.choices
        ctx['estados_proyecto'] = Proyecto.Estado.choices
        ctx['roles'] = MiembroComite.Rol.choices

        comite_id = self.request.GET.get('comite')
        if comite_id and comite_id.isdigit():
            ctx['comite'] = get_object_or_404(Comite.objects.select_related('coordinator'), pk=int(comite_id))
            self._contexto_comite(ctx, ctx['comite'])
        else:
            ctx['comite'] = None
            self._contexto_general(ctx)
        return ctx

    def _tareas(self, qs, mostrar_todas):
        qs = qs.select_related('asignado_a', 'proyecto', 'comite')
        return qs if mostrar_todas else qs.exclude(estado__in=Tarea.CLOSED_STATES)

    def _contexto_comite(self, ctx, comite):
        todas = ctx['mostrar_todas']
        ctx['miembros'] = comite.miembros.select_related('user')
        ids_miembros = set(ctx['miembros'].values_list('user_id', flat=True))
        ctx['usuarios_comite'] = [u for u in ctx['usuarios'] if u.pk in ids_miembros]
        ctx['usuarios_otros'] = [u for u in ctx['usuarios'] if u.pk not in ids_miembros]
        ctx['miembro_form'] = MiembroForm(comite=comite)

        proyectos = comite.proyectos.select_related('responsable')
        if not todas:
            proyectos = proyectos.exclude(estado=Proyecto.Estado.CERRADO)
        ctx['proyectos'] = proyectos.prefetch_related(
            Prefetch('tareas', queryset=self._tareas(Tarea.objects.all(), todas), to_attr='lista_tareas')
        )
        ctx['tareas_sueltas'] = self._tareas(comite.tareas.filter(proyecto__isnull=True), todas)
        ctx['cerradas'] = comite.tareas.filter(estado__in=Tarea.CLOSED_STATES).count()
        ctx['notas'] = comite.notas.select_related('author')[:30]

    def _contexto_general(self, ctx):
        """Vista general: lo abierto de todos los comités, lo vencido primero."""
        abiertas = (
            Tarea.objects.exclude(estado__in=Tarea.CLOSED_STATES)
            .select_related('asignado_a', 'proyecto', 'comite')
            .order_by('due_date', '-prioridad')
        )
        ctx['vencidas'] = [t for t in abiertas if t.is_overdue]
        grupos = {}
        for t in abiertas:
            grupos.setdefault(t.comite, []).append(t)
        # Comités en su orden; lo sin comité, al final.
        ordenados = [(c, grupos[c]) for c in ctx['comites'] if c in grupos]
        if None in grupos:
            ordenados.append((None, grupos[None]))
        ctx['grupos'] = ordenados
        ctx['total_abiertas'] = len(abiertas)
        ctx['transversales'] = Proyecto.objects.filter(comite__isnull=True).exclude(
            estado=Proyecto.Estado.CERRADO).select_related('responsable')


# ---------------------------------------------------------------------------
# Comités
# ---------------------------------------------------------------------------


@superuser_required
@require_POST
def comite_guardar(request, pk=None):
    comite = get_object_or_404(Comite, pk=pk) if pk else None
    form = ComiteForm(request.POST, instance=comite)
    if form.is_valid():
        comite = form.save()
        messages.success(request, 'Comité guardado.')
        return _volver(request, comite.pk)
    _errores(request, form)
    return _volver(request, pk)


@superuser_required
@require_POST
def comite_eliminar(request, pk):
    comite = get_object_or_404(Comite, pk=pk)
    nombre = comite.name
    comite.delete()
    messages.success(request, f'Se eliminó el comité "{nombre}". Sus proyectos y tareas quedaron sin comité.')
    return redirect('gestion:workspace')


# ---------------------------------------------------------------------------
# Integrantes
# ---------------------------------------------------------------------------


@superuser_required
@require_POST
def miembro_agregar(request, pk):
    comite = get_object_or_404(Comite, pk=pk)
    form = MiembroForm(request.POST, comite=comite)
    if form.is_valid():
        m = form.save(commit=False)
        m.comite = comite
        m.save()
        messages.success(request, f'{m.user.get_full_name() or m.user.email} ahora es integrante.')
    else:
        _errores(request, form)
    return _volver(request, comite.pk)


@superuser_required
@require_POST
def miembro_rol(request, pk):
    m = get_object_or_404(MiembroComite, pk=pk)
    rol = request.POST.get('rol')
    if rol in MiembroComite.Rol.values:
        m.rol = rol
        m.save(update_fields=['rol'])
    return _volver(request, m.comite_id)


@superuser_required
@require_POST
def miembro_quitar(request, pk):
    m = get_object_or_404(MiembroComite.objects.select_related('user'), pk=pk)
    comite_id = m.comite_id
    nombre = m.user.get_full_name() or m.user.email
    m.delete()
    messages.success(request, f'{nombre} ya no es integrante.')
    return _volver(request, comite_id)


# ---------------------------------------------------------------------------
# Proyectos
# ---------------------------------------------------------------------------


@superuser_required
@require_POST
def proyecto_guardar(request, pk=None):
    proyecto = get_object_or_404(Proyecto, pk=pk) if pk else None
    form = ProyectoForm(request.POST, instance=proyecto)
    if form.is_valid():
        p = form.save(commit=False)
        if not p.pk:
            p.created_by = request.user
        p.save()
        messages.success(request, 'Proyecto guardado.')
        return _volver(request, p.comite_id)
    _errores(request, form)
    return _volver(request, proyecto.comite_id if proyecto else request.POST.get('comite'))


@superuser_required
@require_POST
def proyecto_estado(request, pk):
    p = get_object_or_404(Proyecto, pk=pk)
    estado = request.POST.get('estado')
    if estado in Proyecto.Estado.values:
        p.estado = estado
        p.save(update_fields=['estado', 'updated_at'])
    return _volver(request, p.comite_id)


@superuser_required
@require_POST
def proyecto_eliminar(request, pk):
    p = get_object_or_404(Proyecto, pk=pk)
    comite_id, titulo, n = p.comite_id, p.title, p.tareas.count()
    p.delete()
    messages.success(request, f'Se eliminó "{titulo}" y sus {n} tareas.')
    return _volver(request, comite_id)


# ---------------------------------------------------------------------------
# Tareas
# ---------------------------------------------------------------------------


@superuser_required
@require_POST
def tarea_rapida(request):
    """Alta desde la fila "Añadir tarea" de la lista."""
    form = TareaRapidaForm(request.POST)
    comite_id = request.POST.get('comite') or None
    if form.is_valid():
        t = Tarea(
            title=form.cleaned_data['title'].strip(),
            asignado_a=form.cleaned_data['asignado_a'],
            due_date=form.cleaned_data['due_date'],
            proyecto=form.cleaned_data['proyecto'],
            comite_id=comite_id if comite_id and str(comite_id).isdigit() else None,
            created_by=request.user,
        )
        t.save()
    else:
        _errores(request, form)
    return _volver(request, comite_id)


@superuser_required
@require_POST
def tarea_guardar(request, pk=None):
    tarea = get_object_or_404(Tarea, pk=pk) if pk else None
    form = TareaForm(request.POST, instance=tarea)
    if form.is_valid():
        t = form.save(commit=False)
        if not t.pk:
            t.created_by = request.user
        t.save()
        messages.success(request, 'Tarea guardada.')
        return _volver(request, t.comite_id)
    _errores(request, form)
    return _volver(request, tarea.comite_id if tarea else request.POST.get('comite'))


@superuser_required
@require_POST
def tarea_estado(request, pk):
    t = get_object_or_404(Tarea, pk=pk)
    estado = request.POST.get('estado')
    if estado in Tarea.Estado.values:
        t.estado = estado
        t.save()
    return _volver(request, t.comite_id)


@superuser_required
@require_POST
def tarea_eliminar(request, pk):
    t = get_object_or_404(Tarea, pk=pk)
    comite_id = t.comite_id
    t.delete()
    messages.success(request, 'Tarea eliminada.')
    return _volver(request, comite_id)


# ---------------------------------------------------------------------------
# Notas
# ---------------------------------------------------------------------------

NOTA_DESTINOS = {'comite': (Comite, 'comite'), 'proyecto': (Proyecto, 'proyecto'), 'tarea': (Tarea, 'tarea')}


@superuser_required
@require_POST
def nota_agregar(request, kind, pk):
    if kind not in NOTA_DESTINOS:
        return redirect('gestion:workspace')
    model, campo = NOTA_DESTINOS[kind]
    destino = get_object_or_404(model, pk=pk)
    form = NotaForm(request.POST)
    if form.is_valid():
        n = form.save(commit=False)
        n.author = request.user
        setattr(n, campo, destino)
        n.save()
    else:
        messages.error(request, 'La nota no puede estar vacía.')
    comite_id = destino.pk if kind == 'comite' else destino.comite_id
    return _volver(request, comite_id)


@superuser_required
@require_POST
def nota_eliminar(request, pk):
    n = get_object_or_404(Nota, pk=pk)
    destino = n.target
    comite_id = destino.pk if isinstance(destino, Comite) else getattr(destino, 'comite_id', None)
    n.delete()
    return _volver(request, comite_id)
