"""Rediseño del CRM: solo usuarios registrados, estados simplificados.

- Persona desaparece. Integrantes, responsables y asignados pasan a ser
  usuarios de la plataforma. Se conserva lo que ya estaba vinculado a una
  cuenta; las personas sin cuenta se descartan (sus tareas quedan sin asignar).
- Proyecto: IDEA/PLANEACION/EN_CURSO -> ACTIVO; COMPLETADO/CANCELADO -> CERRADO.
- Tarea: EN_REVISION -> EN_PROGRESO.
- Prioridad: BAJA/MEDIA -> NORMAL; ALTA/URGENTE -> ALTA.
- Rol de integrante: SECRETARIO/COLABORADOR -> MIEMBRO.
- Se eliminan Comite.icon, Comite.color y Proyecto.avance.
"""
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def migrar_datos(apps, schema_editor):
    MiembroComite = apps.get_model('gestion', 'MiembroComite')
    Proyecto = apps.get_model('gestion', 'Proyecto')
    Tarea = apps.get_model('gestion', 'Tarea')
    Nota = apps.get_model('gestion', 'Nota')

    vistos = set()
    for m in MiembroComite.objects.select_related('persona').order_by('pk'):
        uid = m.persona.user_id if m.persona_id else None
        if not uid or (m.comite_id, uid) in vistos:
            m.delete()
            continue
        vistos.add((m.comite_id, uid))
        m.user_id = uid
        if m.rol not in ('COORDINADOR', 'MIEMBRO'):
            m.rol = 'MIEMBRO'
        m.save(update_fields=['user', 'rol'])

    estado_proy = {'IDEA': 'ACTIVO', 'PLANEACION': 'ACTIVO', 'EN_CURSO': 'ACTIVO',
                   'PAUSADO': 'PAUSADO', 'COMPLETADO': 'CERRADO', 'CANCELADO': 'CERRADO'}
    prioridad = {'BAJA': 'NORMAL', 'MEDIA': 'NORMAL', 'ALTA': 'ALTA', 'URGENTE': 'ALTA'}
    for p in Proyecto.objects.select_related('responsable'):
        p.responsable_user_id = p.responsable.user_id if p.responsable_id else None
        p.estado = estado_proy.get(p.estado, 'ACTIVO')
        p.prioridad = prioridad.get(p.prioridad, 'NORMAL')
        p.save(update_fields=['responsable_user', 'estado', 'prioridad'])

    for t in Tarea.objects.select_related('asignado_a'):
        t.asignado_user_id = t.asignado_a.user_id if t.asignado_a_id else None
        if t.estado == 'EN_REVISION':
            t.estado = 'EN_PROGRESO'
        t.prioridad = prioridad.get(t.prioridad, 'NORMAL')
        t.save(update_fields=['asignado_user', 'estado', 'prioridad'])

    Nota.objects.filter(persona__isnull=False).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0003_proyecto_avance'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1) Campos nuevos hacia User, temporalmente opcionales.
        migrations.AddField(
            model_name='miembrocomite', name='user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='membresias_comite', to=settings.AUTH_USER_MODEL,
                                    verbose_name='Usuario'),
        ),
        migrations.AddField(
            model_name='proyecto', name='responsable_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='proyectos_a_cargo', to=settings.AUTH_USER_MODEL,
                                    verbose_name='Responsable'),
        ),
        migrations.AddField(
            model_name='tarea', name='asignado_user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='tareas_asignadas', to=settings.AUTH_USER_MODEL,
                                    verbose_name='Responsable'),
        ),
        # 2) Copia de datos y simplificación de estados.
        migrations.RunPython(migrar_datos, migrations.RunPython.noop),
        # 3) Fuera lo que apuntaba a Persona.
        migrations.AlterUniqueTogether(name='miembrocomite', unique_together=set()),
        migrations.RemoveField(model_name='miembrocomite', name='persona'),
        migrations.RemoveField(model_name='miembrocomite', name='is_active'),
        migrations.RemoveField(model_name='miembrocomite', name='notes'),
        migrations.RemoveField(model_name='proyecto', name='responsable'),
        migrations.RemoveField(model_name='tarea', name='asignado_a'),
        migrations.RemoveField(model_name='nota', name='persona'),
        migrations.DeleteModel(name='Persona'),
        # 4) Nombres definitivos y restricciones.
        migrations.RenameField(model_name='proyecto', old_name='responsable_user', new_name='responsable'),
        migrations.RenameField(model_name='tarea', old_name='asignado_user', new_name='asignado_a'),
        migrations.AlterField(
            model_name='miembrocomite', name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                    related_name='membresias_comite', to=settings.AUTH_USER_MODEL,
                                    verbose_name='Usuario'),
        ),
        migrations.AlterUniqueTogether(name='miembrocomite', unique_together={('comite', 'user')}),
        migrations.AlterModelOptions(
            name='miembrocomite',
            options={'ordering': ['rol', 'user__first_name', 'user__last_name'],
                     'verbose_name': 'Integrante', 'verbose_name_plural': 'Integrantes'},
        ),
        migrations.AlterField(
            model_name='miembrocomite', name='rol',
            field=models.CharField(choices=[('COORDINADOR', 'Coordinador'), ('MIEMBRO', 'Miembro')],
                                   default='MIEMBRO', max_length=20, verbose_name='Rol'),
        ),
        migrations.AlterField(
            model_name='miembrocomite', name='joined_at',
            field=models.DateField(default=django.utils.timezone.localdate, verbose_name='Desde'),
        ),
        # 5) Comité y proyecto más simples.
        migrations.RemoveField(model_name='comite', name='icon'),
        migrations.RemoveField(model_name='comite', name='color'),
        migrations.AlterField(
            model_name='comite', name='description',
            field=models.TextField(blank=True, verbose_name='Propósito'),
        ),
        migrations.AlterField(
            model_name='comite', name='coordinator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='comites_coordinados', to=settings.AUTH_USER_MODEL,
                                    verbose_name='Coordinador'),
        ),
        migrations.RemoveField(model_name='proyecto', name='avance'),
        migrations.AlterModelOptions(
            name='proyecto',
            options={'ordering': ['estado', 'due_date', 'title'],
                     'verbose_name': 'Proyecto', 'verbose_name_plural': 'Proyectos'},
        ),
        migrations.AlterField(
            model_name='proyecto', name='estado',
            field=models.CharField(choices=[('ACTIVO', 'Activo'), ('PAUSADO', 'En pausa'), ('CERRADO', 'Cerrado')],
                                   default='ACTIVO', max_length=20, verbose_name='Estado'),
        ),
        migrations.AlterField(
            model_name='proyecto', name='prioridad',
            field=models.CharField(choices=[('NORMAL', 'Normal'), ('ALTA', 'Alta')],
                                   default='NORMAL', max_length=10, verbose_name='Prioridad'),
        ),
        migrations.AlterField(
            model_name='proyecto', name='start_date',
            field=models.DateField(blank=True, null=True, verbose_name='Inicio'),
        ),
        migrations.AlterField(
            model_name='proyecto', name='comite',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                    related_name='proyectos', to='gestion.comite', verbose_name='Comité'),
        ),
        # 6) Tarea.
        migrations.AlterModelOptions(
            name='tarea',
            options={'ordering': ['due_date', '-prioridad', 'created_at'],
                     'verbose_name': 'Tarea', 'verbose_name_plural': 'Tareas'},
        ),
        migrations.AlterField(
            model_name='tarea', name='title',
            field=models.CharField(max_length=200, verbose_name='Tarea'),
        ),
        migrations.AlterField(
            model_name='tarea', name='description',
            field=models.TextField(blank=True, verbose_name='Detalle'),
        ),
        migrations.AlterField(
            model_name='tarea', name='estado',
            field=models.CharField(choices=[('PENDIENTE', 'Pendiente'), ('EN_PROGRESO', 'En progreso'),
                                            ('COMPLETADA', 'Completada'), ('CANCELADA', 'Cancelada')],
                                   default='PENDIENTE', max_length=20, verbose_name='Estado'),
        ),
        migrations.AlterField(
            model_name='tarea', name='prioridad',
            field=models.CharField(choices=[('NORMAL', 'Normal'), ('ALTA', 'Alta')],
                                   default='NORMAL', max_length=10, verbose_name='Prioridad'),
        ),
        # 7) Nota.
        migrations.AlterModelOptions(
            name='nota',
            options={'ordering': ['-created_at'], 'verbose_name': 'Nota', 'verbose_name_plural': 'Notas'},
        ),
    ]
