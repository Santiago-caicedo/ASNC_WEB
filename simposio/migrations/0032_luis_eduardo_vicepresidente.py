from django.db import migrations

# Luis Eduardo Jaimes: «Junta Directiva AsNC» becomes «Vicepresidente Junta
# Directiva AsNC» (his Thursday talk and Panel 1).
CHANGES = (
    ('Luis Eduardo Jaimes, Junta Directiva AsNC', 'Luis Eduardo Jaimes, Vicepresidente Junta Directiva AsNC'),
    ('Luis Eduardo Jaimes (Junta Directiva AsNC)', 'Luis Eduardo Jaimes (Vicepresidente Junta Directiva AsNC)'),
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
        ('simposio', '0031_ricardo_munoz_y_cambio_ian_r1'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
