from django.db import migrations

# Carlos Cárdenas' seat on Thursday's Panel 1 is still to be confirmed (his
# Friday talk is not): «Nombre*» shows an asterisk and a «* Por confirmar» note.
CHANGES = (
    ('y Carlos Cárdenas (', 'y Carlos Cárdenas* ('),
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
        ('simposio', '0016_christian_moreno_cargo'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
