"""Gestión de comités en una sola pantalla.

``WorkspaceView`` dibuja todo: la lista de comités y, del comité elegido, sus
proyectos (tarjetas con avance), sus tareas por horizonte de vencimiento,
sus integrantes y sus notas. El resto son acciones POST que
guardan y vuelven a la misma pantalla. Acceso solo para superadministradores.
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import TemplateView

from admissions.views import SuperuserRequiredMixin

from .forms import (
    ComiteForm, MiembroForm, NotaForm, ProyectoForm, TareaForm, TareaRapidaForm, usuarios_activos,
)
from .models import Comite, MiembroComite, Nota, Prioridad, Proyecto, Tarea


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


HORIZONTES = (
    ('vencidas', 'Vencidas', 'Se pasó la fecha límite. Reprográmalas o ciérralas.'),
    ('hoy', 'Hoy', ''),
    ('semana', 'Próximos 7 días', ''),
    ('luego', 'Más adelante', ''),
    ('sin_fecha', 'Sin fecha', 'Ponles fecha para que aparezcan en el plan.'),
)


def agrupar_por_horizonte(tareas, hoy):
    """Reparte tareas abiertas en Vencidas / Hoy / 7 días / Más adelante / Sin fecha."""
    grupos = {k: [] for k, _, _ in HORIZONTES}
    for t in tareas:
        if t.is_closed:
            continue
        if not t.due_date:
            grupos['sin_fecha'].append(t)
        elif t.due_date < hoy:
            grupos['vencidas'].append(t)
        elif t.due_date == hoy:
            grupos['hoy'].append(t)
        elif t.due_date <= hoy + timedelta(days=7):
            grupos['semana'].append(t)
        else:
            grupos['luego'].append(t)
    return [(k, titulo, ayuda, grupos[k]) for k, titulo, ayuda in HORIZONTES if grupos[k]]


def proyectos_con_avance(qs):
    """Anota hechas / total (sin canceladas) para el anillo de cada tarjeta."""
    return qs.annotate(
        total=Count('tareas', filter=~Q(tareas__estado=Tarea.Estado.CANCELADA), distinct=True),
        hechas=Count('tareas', filter=Q(tareas__estado=Tarea.Estado.COMPLETADA), distinct=True),
    )


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
        ctx['usuarios'] = usuarios_activos()
        ctx['comite_form'] = ComiteForm()
        ctx['proyecto_form'] = ProyectoForm()
        ctx['tarea_form'] = TareaForm()
        ctx['estados_proyecto'] = Proyecto.Estado.choices
        ctx['roles'] = MiembroComite.Rol.choices

        comite_id = self.request.GET.get('comite')
        if comite_id and comite_id.isdigit():
            ctx['comite'] = get_object_or_404(Comite.objects.select_related('coordinator'), pk=int(comite_id))
            self._contexto_comite(ctx, ctx['comite'], hoy)
        else:
            ctx['comite'] = None
            self._contexto_general(ctx, hoy)
        return ctx

    def _contexto_comite(self, ctx, comite, hoy):
        ctx['miembros'] = comite.miembros.select_related('user')
        ids = set(ctx['miembros'].values_list('user_id', flat=True))
        ctx['usuarios_comite'] = [u for u in ctx['usuarios'] if u.pk in ids]
        ctx['usuarios_otros'] = [u for u in ctx['usuarios'] if u.pk not in ids]

        proyectos = list(proyectos_con_avance(comite.proyectos.select_related('responsable')))
        ctx['proyectos'] = [p for p in proyectos if p.estado != Proyecto.Estado.CERRADO]
        ctx['proyectos_cerrados'] = [p for p in proyectos if p.estado == Proyecto.Estado.CERRADO]

        # Tarjeta seleccionada: la lista de tareas se limita a ese proyecto.
        sel = self.request.GET.get('proyecto')
        ctx['proyecto_sel'] = next((p for p in proyectos if sel and sel.isdigit() and p.pk == int(sel)), None)

        tareas = comite.tareas.select_related('asignado_a', 'proyecto').order_by('due_date', '-prioridad', 'created_at')
        if ctx['proyecto_sel']:
            tareas = tareas.filter(proyecto=ctx['proyecto_sel'])
        tareas = list(tareas)
        ctx['horizontes'] = agrupar_por_horizonte(tareas, hoy)
        ctx['cerradas'] = [t for t in tareas if t.is_closed][:50]
        abiertas = [t for t in tareas if not t.is_closed]
        ctx['resumen'] = {
            'abiertas': len(abiertas),
            'vencidas': sum(1 for t in abiertas if t.due_date and t.due_date < hoy),
            'semana': sum(1 for t in abiertas if t.due_date and hoy <= t.due_date <= hoy + timedelta(days=7)),
            'sin_responsable': sum(1 for t in abiertas if not t.asignado_a_id),
        }
        ctx['notas'] = comite.notas.select_related('author')[:30]

    def _contexto_general(self, ctx, hoy):
        """Vista general: todo lo abierto de todos los comités, por horizonte."""
        tareas = list(
            Tarea.objects.exclude(estado__in=Tarea.CLOSED_STATES)
            .select_related('asignado_a', 'proyecto', 'comite')
            .order_by('due_date', '-prioridad')
        )
        ctx['horizontes'] = agrupar_por_horizonte(tareas, hoy)
        ctx['resumen'] = {
            'abiertas': len(tareas),
            'vencidas': sum(1 for t in tareas if t.due_date and t.due_date < hoy),
            'semana': sum(1 for t in tareas if t.due_date and hoy <= t.due_date <= hoy + timedelta(days=7)),
            'sin_responsable': sum(1 for t in tareas if not t.asignado_a_id),
        }
        ctx['transversales'] = list(proyectos_con_avance(
            Proyecto.objects.filter(comite__isnull=True).exclude(estado=Proyecto.Estado.CERRADO)
            .select_related('responsable')
        ))


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
            prioridad=Prioridad.ALTA if form.cleaned_data['alta'] else Prioridad.NORMAL,
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
