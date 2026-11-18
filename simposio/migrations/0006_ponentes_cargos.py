from django.db import migrations

# Full names and positions of the speakers, and the moderator of Panel 1.
CHANGES = (
    ('| Laura, WiN Colombia', '| Laura Forero Rodríguez, WiN Colombia'),
    ('Karen Ibarra (WiN Colombia)', 'Karen Ibarra (Presidenta de WiN Colombia)'),
    ('| Carlos Cárdenas, ACIEM', '| Carlos Cárdenas, Presidente Nacional de ACIEM'),
    ('Carlos Cárdenas (ACIEM, virtual)', 'Carlos Cárdenas (Presidente Nacional de ACIEM, virtual)'),
    (
        'y Carlos Cárdenas (Presidente Nacional de ACIEM, virtual)\n',
        'y Carlos Cárdenas (Presidente Nacional de ACIEM, virtual); '
        'Modera: Santiago Caicedo (Vicepresidente ejecutivo, AsNC)\n',
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
    replace_in_agenda(apps, [(new, old) for old, new in reversed(CHANGES)])


class Migration(migrations.Migration):

    dependencies = [
        ('simposio', '0005_dario_cruz_virtual'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
