"""Gestión de comités: integrantes, proyectos, tareas y notas.

Solo intervienen usuarios registrados en la plataforma. Todo se maneja desde
una sola pantalla (ver ``views.WorkspaceView``). Acceso: superadministradores.
"""
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify


class Prioridad(models.TextChoices):
    NORMAL = 'NORMAL', 'Normal'
    ALTA = 'ALTA', 'Alta'


class Comite(models.Model):
    """Un comité de trabajo de la Asociación."""

    name = models.CharField('Nombre', max_length=120, unique=True)
    slug = models.SlugField('Slug', max_length=140, unique=True, blank=True)
    description = models.TextField('Propósito', blank=True)
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='comites_coordinados', verbose_name='Coordinador',
    )
    is_active = models.BooleanField('Activo', default=True)
    order = models.PositiveIntegerField('Orden', default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Comité'
        verbose_name_plural = 'Comités'
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('gestion:workspace') + f'?comite={self.pk}'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'comite'
            slug, n = base, 2
            while Comite.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def open_tasks_count(self):
        return self.tareas.exclude(estado__in=Tarea.CLOSED_STATES).count()


class MiembroComite(models.Model):
    """Pertenencia de un usuario registrado a un comité."""

    class Rol(models.TextChoices):
        COORDINADOR = 'COORDINADOR', 'Coordinador'
        MIEMBRO = 'MIEMBRO', 'Miembro'

    comite = models.ForeignKey(Comite, on_delete=models.CASCADE, related_name='miembros')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='membresias_comite', verbose_name='Usuario',
    )
    rol = models.CharField('Rol', max_length=20, choices=Rol.choices, default=Rol.MIEMBRO)
    joined_at = models.DateField('Desde', default=timezone.localdate)

    class Meta:
        verbose_name = 'Integrante'
        verbose_name_plural = 'Integrantes'
        unique_together = [('comite', 'user')]
        ordering = ['rol', 'user__first_name', 'user__last_name']

    def __str__(self):
        return f'{self.user.get_full_name() or self.user.email} · {self.comite}'


class Proyecto(models.Model):
    """Una iniciativa de un comité, o transversal si no tiene comité."""

    class Estado(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        PAUSADO = 'PAUSADO', 'En pausa'
        CERRADO = 'CERRADO', 'Cerrado'

    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descripción', blank=True)
    comite = models.ForeignKey(
        Comite, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='proyectos', verbose_name='Comité',
    )
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='proyectos_a_cargo', verbose_name='Responsable',
    )
    estado = models.CharField('Estado', max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    prioridad = models.CharField('Prioridad', max_length=10, choices=Prioridad.choices, default=Prioridad.NORMAL)
    start_date = models.DateField('Inicio', null=True, blank=True)
    due_date = models.DateField('Fecha objetivo', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['estado', 'due_date', 'title']

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return bool(self.due_date and self.estado != self.Estado.CERRADO
                    and self.due_date < timezone.localdate())


class Tarea(models.Model):
    """Una unidad de trabajo, con o sin proyecto, asignada a un usuario."""

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_PROGRESO = 'EN_PROGRESO', 'En progreso'
        COMPLETADA = 'COMPLETADA', 'Completada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    CLOSED_STATES = (Estado.COMPLETADA, Estado.CANCELADA)

    title = models.CharField('Tarea', max_length=200)
    description = models.TextField('Detalle', blank=True)
    comite = models.ForeignKey(
        Comite, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tareas', verbose_name='Comité',
    )
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, null=True, blank=True,
        related_name='tareas', verbose_name='Proyecto',
    )
    asignado_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tareas_asignadas', verbose_name='Responsable',
    )
    estado = models.CharField('Estado', max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    prioridad = models.CharField('Prioridad', max_length=10, choices=Prioridad.choices, default=Prioridad.NORMAL)
    due_date = models.DateField('Fecha límite', null=True, blank=True)
    completed_at = models.DateTimeField('Completada el', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['due_date', '-prioridad', 'created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.estado == self.Estado.COMPLETADA and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.estado != self.Estado.COMPLETADA:
            self.completed_at = None
        # Una tarea sin comité hereda el del proyecto.
        if self.proyecto_id and not self.comite_id:
            self.comite_id = self.proyecto.comite_id
        super().save(*args, **kwargs)

    @property
    def is_closed(self):
        return self.estado in self.CLOSED_STATES

    @property
    def is_done(self):
        return self.estado == self.Estado.COMPLETADA

    @property
    def is_overdue(self):
        return bool(self.due_date and not self.is_closed and self.due_date < timezone.localdate())


class Nota(models.Model):
    """Nota de seguimiento sobre un comité, un proyecto o una tarea."""

    content = models.TextField('Nota')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+',
    )
    comite = models.ForeignKey(Comite, on_delete=models.CASCADE, null=True, blank=True, related_name='notas')
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, null=True, blank=True, related_name='notas')
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, null=True, blank=True, related_name='notas')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
        ordering = ['-created_at']

    def __str__(self):
        return self.content[:60]

    @property
    def target(self):
        return self.tarea or self.proyecto or self.comite
