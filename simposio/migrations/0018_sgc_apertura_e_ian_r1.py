from django.db import migrations

# The Servicio Geológico Colombiano joins the Thursday programme:
# - Opening talk: Jimmy Alejandro Muñoz, Director de Asuntos Nucleares (por confirmar).
# - Andrea Sánchez takes Daniel Herrera's slot (he no longer speaks) with a talk on
#   the IAN-R1 research reactor as a teaching reactor. Both titles are provisional.
CHANGES = (
    (
        '| Radiación y protección radiológica | Por confirmar',
        '| Colombia nuclear hoy: aplicaciones en el país y la proyección del Servicio Geológico Colombiano'
        ' | Jimmy Alejandro Muñoz*, Director de Asuntos Nucleares del Servicio Geológico Colombiano',
    ),
    (
        '| Panorama actual de la energía nuclear: centrales convencionales y SMR'
        ' | Daniel Herrera, Director de Relaciones Estratégicas, AsNC',
        '| IAN-R1: el reactor que puede formar a la nueva generación nuclear de Colombia'
        ' | Andrea Sánchez, Servicio Geológico Colombiano',
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
        ('simposio', '0017_carlos_cardenas_por_confirmar'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
