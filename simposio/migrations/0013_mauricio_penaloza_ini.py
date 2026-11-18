from django.db import migrations

# INI's ally talk (Thursday 11:10) is given by Mauricio Peñaloza, its manager.
CHANGES = (
    (
        '11:10 – 11:30 | Charla de aliado institucional | International Nuclear Industry (INI)',
        '11:10 – 11:30 | Charla de aliado institucional | Mauricio Peñaloza, Gerente INI | Aliado',
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
        ('simposio', '0012_upme_director_mayuscula'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
