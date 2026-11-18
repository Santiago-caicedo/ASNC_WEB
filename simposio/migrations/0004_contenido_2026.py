import datetime

from django.db import migrations

SEED_TITLE = 'Simposio Nuclear Colombiano'

DESCRIPTION = (
    'El primer espacio académico y técnico dedicado a la energía nuclear en el Caribe '
    'colombiano. Reúne a expertos, estudiantes, investigadores, profesionales y '
    'organizaciones para dialogar sobre el papel de la ciencia y la tecnología nuclear '
    'en la transición energética del país.'
)

# Agenda tentativa v4. One line per activity: «hora | actividad | ponente».
AGENDA = """Jueves 3 de diciembre
7:30 – 8:30 | Registro y bienvenida |
8:30 – 9:05 | Radiación y protección radiológica | Jhon Aponte, QA Positron
9:05 – 9:40 | Funcionamiento de una central nuclear | Herling Gonzales, AsNC
9:40 – 10:00 | Café |
10:00 – 10:35 | Ley nuclear y marco regulatorio colombiano | Laura, WiN Colombia
10:35 – 11:10 | Panorama actual de la energía nuclear: centrales convencionales y SMR | Daniel Herrera, AsNC
11:10 – 11:30 | Charla de aliado institucional | International Nuclear Industry (INI)
11:30 – 11:50 | Charla de aliado institucional |
11:50 – 13:30 | Almuerzo |
14:25 – 15:00 | Mirada de la UPME sobre la matriz eléctrica y energética del país | Rafael Fragozo, director de la UPME
15:00 – 16:15 | Panel 1. Energía nuclear: rol frente a la transición energética | Karen Ibarra (WiN Colombia), Luis Eduardo Jaimes (AsNC / UNAB), Diana Montaña (UPME) y Carlos Cárdenas (ACIEM, virtual)
Viernes 4 de diciembre
8:00 – 8:35 | Perspectiva de la energía nuclear en la región Caribe | Christian Moreno, CUC
8:35 – 8:55 | Charla de aliado institucional |
8:55 – 9:15 | Café |
9:15 – 9:50 | El gremio de la ingeniería en el desarrollo de la energía nuclear | Carlos Cárdenas, ACIEM
9:50 – 10:25 | Fusión nuclear | Darío Cruz, Fusenet
10:25 – 11:45 | Panel 2. Educación y construcción de capacidades para el entorno nuclear colombiano | Adriana Rincón y Lourdes Meriño (Universidad del Atlántico), Darío Cruz (Fusenet) y Christian Moreno (CUC)
11:45 – 12:00 | Clausura |"""


def fill(apps, schema_editor):
    """Load the 2026 edition's content into the seeded row, if nobody edited it yet."""
    Simposio = apps.get_model('simposio', 'Simposio')
    simposio = Simposio.objects.filter(title=SEED_TITLE, description='', agenda='').first()
    if simposio is None:
        return
    simposio.title = 'Primer Simposio de Energía Nuclear'
    simposio.hero_kicker = 'Primer simposio'
    simposio.hero_title = 'Energía Nuclear'
    simposio.tagline = 'Ciencia, tecnología y sociedad para el desarrollo de Colombia'
    simposio.description = DESCRIPTION
    simposio.starts_on = datetime.date(2026, 12, 3)
    simposio.ends_on = datetime.date(2026, 12, 4)
    simposio.schedule_text = 'Jueves y viernes, desde las 7:30 a. m.'
    simposio.venue = 'Centro de Convenciones, Universidad del Atlántico'
    simposio.city = 'Barranquilla'
    simposio.agenda = AGENDA
    simposio.save()


class Migration(migrations.Migration):

    dependencies = [
        ('simposio', '0003_portada'),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
