from django.db import migrations

CHANGES = (
    ('Luis Eduardo Jaimes (AsNC / UNAB)', 'Luis Eduardo Jaimes (Junta Directiva AsNC)'),
    ('Santiago Caicedo (Vicepresidente ejecutivo, AsNC)', 'Santiago Caicedo (Vicepresidente Ejecutivo AsNC)'),
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
        ('simposio', '0018_sgc_apertura_e_ian_r1'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
