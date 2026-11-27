from django.db import migrations

# - Thursday 8:30 opening («Por definir») goes to Ricardo Muñoz Ibáñez (medical
#   physicist, Clínica Bonnadona Prevenir) on radiation protection.
# - Luis Eduardo Jaimes and the IAN-R1 talk swap places (both 35 min): his El Niño
#   talk moves to Thursday 10:35 and the IAN-R1 talk, now given by Mauricio López
#   (SGC, reactor coordinator), moves to Friday 8:55.
OPENING = (
    '8:30 – 9:05 | Por definir | Por definir',
    '8:30 – 9:05 | Presente y futuro de la protección radiológica en la era nuclear de Colombia'
    ' | Ricardo Muñoz Ibáñez, Físico médico de la Clínica Bonnadona Prevenir',
)
IAN_THURSDAY = (
    '10:35 – 11:10 | IAN-R1: el reactor que puede formar a la nueva generación nuclear de Colombia'
    ' | Por confirmar'
)
NINO_FRIDAY = (
    '8:55 – 9:30 | Relación del fenómeno del Niño y la energía nuclear en la seguridad energética'
    ' de Colombia | Luis Eduardo Jaimes, Junta Directiva AsNC'
)
NINO_THURSDAY = (
    '10:35 – 11:10 | Relación del fenómeno del Niño y la energía nuclear en la seguridad energética'
    ' de Colombia | Luis Eduardo Jaimes, Junta Directiva AsNC'
)
IAN_FRIDAY = (
    '8:55 – 9:30 | IAN-R1: el reactor que puede formar a la nueva generación nuclear de Colombia'
    ' | Mauricio López, Coordinador del reactor IAN-R1, Servicio Geológico Colombiano'
)


def apply(apps, pairs):
    Simposio = apps.get_model('simposio', 'Simposio')
    for simposio in Simposio.objects.all():
        lines = simposio.agenda.replace('\r\n', '\n').split('\n')
        olds = [old for old, _ in pairs]
        # Only when every line is still as we left it (nobody edited it by hand).
        if not all(old in lines for old in olds):
            continue
        mapping = dict(pairs)
        new_lines = [mapping.get(line, line) for line in lines]
        simposio.agenda = '\n'.join(new_lines)
        simposio.save(update_fields=['agenda'])


FORWARD = [OPENING, (IAN_THURSDAY, NINO_THURSDAY), (NINO_FRIDAY, IAN_FRIDAY)]


def update(apps, schema_editor):
    apply(apps, FORWARD)


def revert(apps, schema_editor):
    apply(apps, [(new, old) for old, new in FORWARD])


class Migration(migrations.Migration):

    dependencies = [
        ('simposio', '0030_daniel_virtual_dario_executive_officer'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
