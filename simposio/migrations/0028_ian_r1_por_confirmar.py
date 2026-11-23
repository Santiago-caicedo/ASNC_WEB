from django.db import migrations

# The IAN-R1 talk (Thursday 10:35) keeps its title; its speaker is «Por confirmar».
CHANGES = (
    (
        '| IAN-R1: el reactor que puede formar a la nueva generación nuclear de Colombia'
        ' | Participante delegado del Servicio Geológico Colombiano',
        '| IAN-R1: el reactor que puede formar a la nueva generación nuclear de Colombia'
        ' | Por confirmar',
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
        ('simposio', '0027_ini_instrumentacion_nuclear'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
