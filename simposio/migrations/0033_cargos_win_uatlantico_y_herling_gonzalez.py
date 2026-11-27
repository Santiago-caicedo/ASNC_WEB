from django.db import migrations

# - WiN Colombia is written out: «Women in Nuclear Colombia» (Karen Ibarra and Laura Forero).
# - The Universidad del Atlántico professors (Panel 2) get «Docente e investigadora».
# - Herling's surname is Gonzalez, with a final z.
CHANGES = (
    ('Karen Ibarra (Presidenta de WiN Colombia)', 'Karen Ibarra (Presidenta de Women in Nuclear Colombia)'),
    ('Laura Forero Rodríguez, WiN Colombia', 'Laura Forero Rodríguez, Women in Nuclear Colombia'),
    (
        'Adriana Rincón y Lourdes Meriño (Universidad del Atlántico)',
        'Adriana Rincón y Lourdes Meriño (Docente e investigadora Universidad del Atlántico)',
    ),
    ('Herling Gonzales,', 'Herling Gonzalez,'),
)


def replace_in_agenda(apps, changes):
    Simposio = apps.get_model('simposio', 'Simposio')
    for simposio in Simposio.objects.all():
        agenda = simposio.agenda
        for old, new in changes:
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
        ('simposio', '0032_luis_eduardo_vicepresidente'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
