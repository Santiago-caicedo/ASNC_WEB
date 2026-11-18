from django.db import migrations

# Darío Cruz is the CEO of Fusenet and takes part remotely in both sessions.
CHANGES = (
    ('| Darío Cruz, Fusenet', '| Darío Cruz, CEO de Fusenet, virtual'),
    ('Darío Cruz (Fusenet)', 'Darío Cruz (CEO de Fusenet, virtual)'),
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
        ('simposio', '0004_contenido_2026'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
