from django.db import migrations

# Carlos Cárdenas leaves Thursday's Panel 1 and joins Friday's Panel 2, in person
# (no longer «virtual» nor «por confirmar»).
CHANGES = (
    (
        '), Diana Montaña (UPME) y Carlos Cárdenas* (Presidente Nacional de ACIEM, virtual)',
        ') y Diana Montaña (UPME)',
    ),
    (
        ' y Christian Moreno (Docente e investigador Universitario CUC)',
        ', Christian Moreno (Docente e investigador Universitario CUC)'
        ' y Carlos Cárdenas (Presidente Nacional de ACIEM)',
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
        ('simposio', '0022_daniel_herrera_titulo'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
