from django.db import migrations

# Jimmy Alejandro Muñoz and Andrea Sánchez leave the Thursday programme.
# - The opening talk stays in its slot with title and speaker «Por definir».
# - The IAN-R1 talk keeps its title; the SGC will send a delegate.
CHANGES = (
    (
        '| Colombia nuclear hoy: aplicaciones en el país y la proyección del Servicio Geológico Colombiano'
        ' | Jimmy Alejandro Muñoz*, Director de Asuntos Nucleares del Servicio Geológico Colombiano',
        '| Por definir | Por definir',
    ),
    (
        '| IAN-R1: el reactor que puede formar a la nueva generación nuclear de Colombia'
        ' | Andrea Sánchez, Servicio Geológico Colombiano',
        '| IAN-R1: el reactor que puede formar a la nueva generación nuclear de Colombia'
        ' | Participante delegado del Servicio Geológico Colombiano',
    ),
)


def replace_in_agenda(apps, changes):
    Simposio = apps.get_model('simposio', 'Simposio')
    for simposio in Simposio.objects.all():
        agenda = simposio.agenda
        for old, new in changes:
            if old in agenda:
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
        ('simposio', '0025_conferencias'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
