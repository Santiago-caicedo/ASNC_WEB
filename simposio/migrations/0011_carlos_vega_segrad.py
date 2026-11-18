from django.db import migrations

# Carlos Alberto Vega Pacheco gives the ally talk on behalf of SEGRAD.
CHANGES = (
    (
        '| Carlos Alberto Vega Pacheco | Aliado',
        '| Carlos Alberto Vega Pacheco, SEGRAD | Aliado',
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
        ('simposio', '0010_ponente_por_confirmar'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
