from django.db import migrations

# - Daniel Herrera gives his Thursday 11:30 talk remotely (same «Virtual» tag as Darío).
# - Darío Cruz: «CEO de Fusenet» becomes «Executive Officer de Fusenet» (talk and Panel 2).
CHANGES = (
    (
        '| Daniel Herrera, Director de Relaciones Estratégicas, AsNC\n',
        '| Daniel Herrera, Director de Relaciones Estratégicas, AsNC, virtual\n',
    ),
    ('Darío Cruz, CEO de Fusenet, virtual', 'Darío Cruz, Executive Officer de Fusenet, virtual'),
    ('Darío Cruz (CEO de Fusenet, virtual)', 'Darío Cruz (Executive Officer de Fusenet, virtual)'),
)


def replace_in_agenda(apps, changes):
    Simposio = apps.get_model('simposio', 'Simposio')
    for simposio in Simposio.objects.all():
        # A trailing newline lets the Daniel line match even when it is the last one.
        agenda = simposio.agenda.replace('\r\n', '\n') + '\n'
        for old, new in changes:
            agenda = agenda.replace(old, new)
        agenda = agenda[:-1]
        if agenda != simposio.agenda.replace('\r\n', '\n'):
            simposio.agenda = agenda
            simposio.save(update_fields=['agenda'])


def update(apps, schema_editor):
    replace_in_agenda(apps, CHANGES)


def revert(apps, schema_editor):
    replace_in_agenda(apps, [(new, old) for old, new in CHANGES])


class Migration(migrations.Migration):

    dependencies = [
        ('simposio', '0029_inscripcion_lista_de_espera'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
