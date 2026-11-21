from django.db import migrations

# Daniel Herrera returns on Thursday, in the 20-minute slot at 11:30 that was an
# unassigned allies' talk, with the talk he had before (title provisional).
CHANGES = (
    (
        '11:30 – 11:50 | Charla de aliado institucional |',
        '11:30 – 11:50 | Panorama actual de la energía nuclear: centrales convencionales y SMR'
        ' | Daniel Herrera, Director de Relaciones Estratégicas, AsNC',
    ),
)


def replace_in_agenda(apps, changes):
    Simposio = apps.get_model('simposio', 'Simposio')
    for simposio in Simposio.objects.all():
        agenda = simposio.agenda
        for old, new in changes:
            if new not in agenda:
                # Match the whole line so a slot that already has text after «|» is left alone.
                lines = [new if line.strip() == old else line for line in agenda.split('\n')]
                agenda = '\n'.join(lines)
        if agenda != simposio.agenda:
            simposio.agenda = agenda
            simposio.save(update_fields=['agenda'])


def update(apps, schema_editor):
    replace_in_agenda(apps, CHANGES)


def revert(apps, schema_editor):
    replace_in_agenda(apps, [(new, old) for old, new in CHANGES])


class Migration(migrations.Migration):

    dependencies = [
        ('simposio', '0019_jaimes_y_caicedo_cargos'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
