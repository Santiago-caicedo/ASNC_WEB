from django.db import migrations

# Friday: Luis Eduardo Jaimes gives a 35-minute talk at 8:55, right after the
# SEGRAD talk. Coffee and everything after it move 35 minutes later and keep
# their length (the closing ends at 12:35 instead of 12:00).
NEW_TALK = (
    '8:55 – 9:30 | Relación del fenómeno del Niño y la energía nuclear en la seguridad'
    ' energética de Colombia | Luis Eduardo Jaimes, Junta Directiva AsNC'
)
AFTER = '8:35 – 8:55 |'  # the line the new talk goes after
SHIFT = (
    ('8:55 – 9:15 | Café', '9:30 – 9:50 | Café'),
    ('9:15 – 9:50 |', '9:50 – 10:25 |'),
    ('9:50 – 10:25 |', '10:25 – 11:00 |'),
    ('10:25 – 11:45 |', '11:00 – 12:20 |'),
    ('11:45 – 12:00 |', '12:20 – 12:35 |'),
)


def rewrite_friday(agenda, forward):
    lines = agenda.split('\n')
    out, in_friday = [], False
    for line in lines:
        stripped = line.strip()
        if '|' not in stripped:
            in_friday = stripped.lower().startswith('viernes')
            out.append(line)
            continue
        if not in_friday:
            out.append(line)
            continue
        if not forward and stripped == NEW_TALK:
            continue
        pairs = SHIFT if forward else [(new, old) for old, new in reversed(SHIFT)]
        for old, new in pairs:
            if stripped.startswith(old):
                line = new + stripped[len(old):]
                break
        out.append(line)
        if forward and stripped.startswith(AFTER):
            out.append(NEW_TALK)
    return '\n'.join(out)


def apply(apps, forward):
    Simposio = apps.get_model('simposio', 'Simposio')
    for simposio in Simposio.objects.all():
        agenda = simposio.agenda
        already = NEW_TALK in agenda
        if forward == already:
            continue  # already applied (or already reverted)
        if forward and AFTER not in agenda:
            continue  # the programme was edited by hand; leave it alone
        agenda = rewrite_friday(agenda, forward)
        if agenda != simposio.agenda:
            simposio.agenda = agenda
            simposio.save(update_fields=['agenda'])


def update(apps, schema_editor):
    apply(apps, forward=True)


def revert(apps, schema_editor):
    apply(apps, forward=False)


class Migration(migrations.Migration):

    dependencies = [
        ('simposio', '0020_daniel_herrera_vuelve'),
    ]

    operations = [
        migrations.RunPython(update, revert),
    ]
