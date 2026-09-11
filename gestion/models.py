"""Internal CRM for ASNC committees: people, projects, tasks and follow-up notes.

Only superadmins can use it for now (see ``SuperuserRequiredMixin`` in views).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.utils.text import slugify


class Prioridad(models.TextChoices):
    BAJA = 'BAJA', 'Baja'
    MEDIA = 'MEDIA', 'Media'
    ALTA = 'ALTA', 'Alta'
    URGENTE = 'URGENTE', 'Urgente'


class Comite(models.Model):
    """A working committee of the association (seeded with the six public ones)."""

    name = models.CharField('Nombre', max_length=120, unique=True)
    slug = models.SlugField('Slug', max_length=140, unique=True, blank=True)
    description = models.TextField('Descripción / propósito', blank=True)
    icon = models.CharField(
        'Ícono', max_length=60, default='bi-people-fill',
        help_text='Clase de Bootstrap Icons, por ejemplo: bi-megaphone-fill',
    )
    color = models.CharField(
        'Color', max_length=7, default='#213a5c',
        help_text='Color hexadecimal, por ejemplo: #8b5cf6',
    )
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='comites_coordinados', verbose_name='Coordinador (usuario)',
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
        return reverse('gestion:comite_detail', args=[self.pk])

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name) or 'comite'
            slug = base
            n = 2
            while Comite.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f'{base}-{n}'
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def active_members_count(self):
        return self.miembros.filter(is_active=True).count()

    @property
    def open_tasks_count(self):
        return self.tareas.exclude(estado__in=Tarea.CLOSED_STATES).count()

    @property
    def active_projects_count(self):
        return self.proyectos.filter(estado__in=Proyecto.ACTIVE_STATES).count()


class Persona(models.Model):
    """A contact managed in the CRM. May or may not be linked to a platform user."""

    class Tipo(models.TextChoices):
        ASOCIADO = 'ASOCIADO', 'Asociado'
        ALIADO = 'ALIADO', 'Aliado / Contacto externo'
        VOLUNTARIO = 'VOLUNTARIO', 'Voluntario'
        INSTITUCION = 'INSTITUCION', 'Institución'
        PROVEEDOR = 'PROVEEDOR', 'Proveedor'
        OTRO = 'OTRO', 'Otro'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='persona_crm', verbose_name='Usuario de la plataforma',
        help_text='Opcional. Vincula esta persona con una cuenta existente.',
    )
    first_name = models.CharField('Nombres', max_length=100)
    last_name = models.CharField('Apellidos', max_length=100, blank=True)
    email = models.EmailField('Correo electrónico', blank=True)
    phone = models.CharField('Teléfono', max_length=30, blank=True)
    organization = models.CharField('Organización / Institución', max_length=150, blank=True)
    position = models.CharField('Cargo', max_length=120, blank=True)
    tipo = models.CharField('Tipo', max_length=20, choices=Tipo.choices, default=Tipo.ASOCIADO)
    linkedin_url = models.URLField('LinkedIn', blank=True)
    notes = models.TextField('Observaciones', blank=True)
    is_active = models.BooleanField('Activa', default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Persona'
        verbose_name_plural = 'Personas'
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return self.full_name

    def get_absolute_url(self):
        return reverse('gestion:persona_detail', args=[self.pk])

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def initials(self):
        parts = [self.first_name[:1], self.last_name[:1]]
        return ''.join(p for p in parts if p).upper()

    @property
    def open_tasks_count(self):
        return self.tareas_asignadas.exclude(estado__in=Tarea.CLOSED_STATES).count()

    @classmethod
    def from_user(cls, user, created_by=None):
        """Create (or return) the CRM record linked to a platform user."""
        persona = getattr(user, 'persona_crm', None)
        if persona:
            return persona, False
        persona = cls.objects.create(
            user=user,
            first_name=user.first_name or user.email.split('@')[0],
            last_name=user.last_name,
            email=user.email,
            phone=user.phone,
            organization=user.institution,
            position=user.current_job,
            linkedin_url=user.linkedin_url,
            tipo=cls.Tipo.ASOCIADO,
            created_by=created_by,
        )
        return persona, True


class MiembroComite(models.Model):
    """Membership of a person in a committee, with a role."""

    class Rol(models.TextChoices):
        COORDINADOR = 'COORDINADOR', 'Coordinador(a)'
        SECRETARIO = 'SECRETARIO', 'Secretario(a)'
        MIEMBRO = 'MIEMBRO', 'Miembro'
        COLABORADOR = 'COLABORADOR', 'Colaborador(a)'

    comite = models.ForeignKey(Comite, on_delete=models.CASCADE, related_name='miembros')
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, related_name='membresias')
    rol = models.CharField('Rol', max_length=20, choices=Rol.choices, default=Rol.MIEMBRO)
    joined_at = models.DateField('Fecha de ingreso', default=timezone.localdate)
    is_active = models.BooleanField('Activo', default=True)
    notes = models.CharField('Nota', max_length=200, blank=True)

    class Meta:
        verbose_name = 'Miembro de comité'
        verbose_name_plural = 'Miembros de comités'
        unique_together = [('comite', 'persona')]
        ordering = ['rol', 'persona__first_name']

    def __str__(self):
        return f'{self.persona} · {self.comite} ({self.get_rol_display()})'


class Proyecto(models.Model):
    """An initiative owned by a committee (or transversal to the association)."""

    class Estado(models.TextChoices):
        IDEA = 'IDEA', 'Idea'
        PLANEACION = 'PLANEACION', 'En planeación'
        EN_CURSO = 'EN_CURSO', 'En curso'
        PAUSADO = 'PAUSADO', 'Pausado'
        COMPLETADO = 'COMPLETADO', 'Completado'
        CANCELADO = 'CANCELADO', 'Cancelado'

    ACTIVE_STATES = (Estado.PLANEACION, Estado.EN_CURSO)
    CLOSED_STATES = (Estado.COMPLETADO, Estado.CANCELADO)

    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descripción', blank=True)
    comite = models.ForeignKey(
        Comite, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='proyectos', verbose_name='Comité',
        help_text='Dejar vacío para un proyecto transversal de la Asociación.',
    )
    responsable = models.ForeignKey(
        Persona, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='proyectos_liderados', verbose_name='Responsable',
    )
    estado = models.CharField('Estado', max_length=20, choices=Estado.choices, default=Estado.IDEA)
    prioridad = models.CharField('Prioridad', max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    start_date = models.DateField('Fecha de inicio', null=True, blank=True)
    due_date = models.DateField('Fecha objetivo', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Proyecto'
        verbose_name_plural = 'Proyectos'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('gestion:proyecto_detail', args=[self.pk])

    @property
    def is_active(self):
        return self.estado in self.ACTIVE_STATES

    @property
    def is_overdue(self):
        return bool(
            self.due_date
            and self.estado not in self.CLOSED_STATES
            and self.due_date < timezone.localdate()
        )

    @property
    def tasks_total(self):
        return self.tareas.exclude(estado=Tarea.Estado.CANCELADA).count()

    @property
    def tasks_done(self):
        return self.tareas.filter(estado=Tarea.Estado.COMPLETADA).count()

    @property
    def progress(self):
        total = self.tasks_total
        if not total:
            return 100 if self.estado == self.Estado.COMPLETADO else 0
        return int(self.tasks_done * 100 / total)


class Tarea(models.Model):
    """A unit of work, optionally tied to a committee, a project and an assignee."""

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_PROGRESO = 'EN_PROGRESO', 'En progreso'
        EN_REVISION = 'EN_REVISION', 'En revisión'
        COMPLETADA = 'COMPLETADA', 'Completada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    CLOSED_STATES = (Estado.COMPLETADA, Estado.CANCELADA)
    BOARD_STATES = (Estado.PENDIENTE, Estado.EN_PROGRESO, Estado.EN_REVISION, Estado.COMPLETADA)

    title = models.CharField('Título', max_length=200)
    description = models.TextField('Descripción', blank=True)
    comite = models.ForeignKey(
        Comite, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tareas', verbose_name='Comité',
    )
    proyecto = models.ForeignKey(
        Proyecto, on_delete=models.CASCADE, null=True, blank=True,
        related_name='tareas', verbose_name='Proyecto',
    )
    asignado_a = models.ForeignKey(
        Persona, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tareas_asignadas', verbose_name='Asignada a',
    )
    estado = models.CharField('Estado', max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    prioridad = models.CharField('Prioridad', max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    due_date = models.DateField('Fecha límite', null=True, blank=True)
    completed_at = models.DateTimeField('Completada el', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
        ordering = ['due_date', '-prioridad', '-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('gestion:tarea_detail', args=[self.pk])

    def save(self, *args, **kwargs):
        if self.estado == self.Estado.COMPLETADA and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.estado != self.Estado.COMPLETADA:
            self.completed_at = None
        # A task inherits the committee of its project when none was given.
        if self.proyecto_id and not self.comite_id:
            self.comite_id = self.proyecto.comite_id
        super().save(*args, **kwargs)

    @property
    def is_closed(self):
        return self.estado in self.CLOSED_STATES

    @property
    def is_overdue(self):
        return bool(self.due_date and not self.is_closed and self.due_date < timezone.localdate())


class Nota(models.Model):
    """Follow-up note / activity entry attached to a committee, person, project or task."""

    content = models.TextField('Nota')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+',
    )
    comite = models.ForeignKey(Comite, on_delete=models.CASCADE, null=True, blank=True, related_name='notas')
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE, null=True, blank=True, related_name='notas')
    proyecto = models.ForeignKey(Proyecto, on_delete=models.CASCADE, null=True, blank=True, related_name='notas')
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, null=True, blank=True, related_name='notas')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Nota de seguimiento'
        verbose_name_plural = 'Notas de seguimiento'
        ordering = ['-created_at']

    def __str__(self):
        return self.content[:60]

    @property
    def target(self):
        return self.tarea or self.proyecto or self.persona or self.comite
