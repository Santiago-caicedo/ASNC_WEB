from django.db import migrations, models

# Friday's 8:35 ally talk now has its title and speaker.
CHANGES = (
    (
        '8:35 – 8:55 | Charla de aliado institucional |',
        '8:35 – 8:55 | El rol del oficial de protección radiológica | Carlos Alberto Vega Pacheco | Aliado',
    ),
)


def replace_in_agenda(apps, changes):
    Simposio = apps.get_model('simposio', 'Simposio')
    for simposio in Simposio.objects.all():
        agenda = simposio.agenda
        for old, new in changes:
            if new not in agenda:
                agenda = agenda.replace(old, new)
        if agenda != simposio.agenda:
            simposio.agenda = agenda
            simposio.save(update_fields=['agenda'])


def update(apps, schema_editor):
    replace_in_agenda(apps, CHANGES)


def revert(apps, schema_editor):
    replace_in_agenda(apps, [(new, old) for old, new in CHANGES])


class Migration(migrations.Migration):

    dependencies = [
        ('simposio', '0007_daniel_herrera_cargo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='simposio',
            name='agenda',
            field=models.TextField(blank=True, help_text='Una línea por actividad con el formato «hora | actividad | ponente». Una línea sin «|» se muestra como encabezado (por ejemplo, el día). Agrega «| Aliado» al final para marcar la charla de un aliado.', verbose_name='Programa'),
        ),
        migrations.RunPython(update, revert),
    ]
