from django.db import migrations

# Jhon Aponte no longer gives the radiation talk; its speaker is to be confirmed.
CHANGES = (
    (
        '| Radiación y protección radiológica | Jhon Aponte, QA Positron',
        '| Radiación y protección radiológica | Por confirmar',
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
        ('simposio', '0009_inscripcion_modalidad'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
