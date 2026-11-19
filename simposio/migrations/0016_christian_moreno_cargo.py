from django.db import migrations

ROLE = 'Docente e investigador Universitario CUC'
CHANGES = (
    ('| Christian Moreno, CUC', f'| Christian Moreno, {ROLE}'),
    ('y Christian Moreno (CUC)', f'y Christian Moreno ({ROLE})'),
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
        ('simposio', '0015_herling_comite_cientifico'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
