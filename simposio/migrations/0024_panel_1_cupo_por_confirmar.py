from django.db import migrations

# Thursday's Panel 1 gets an open seat: the web shows a blank avatar with
# «Por confirmar» (the agenda PDF leaves it out).
CHANGES = (
    (
        ') y Diana Montaña (UPME); Modera:',
        '), Diana Montaña (UPME) y Por confirmar; Modera:',
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
        ('simposio', '0023_carlos_cardenas_panel_2'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
