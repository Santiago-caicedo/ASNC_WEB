"""Seed the six committees shown on the public 'Quiénes somos' page."""
from django.db import migrations

COMITES = [
    ('Comité de Divulgación', 'Comunicación, contenido educativo y presencia en redes sociales.', 'bi-megaphone-fill', '#8b5cf6'),
    ('Comité Científico', 'Validación científica, investigación y asesoría especializada.', 'bi-cpu-fill', '#0ea5e9'),
    ('Comité de Regulación y Gobierno', 'Asuntos regulatorios, políticas públicas y relaciones institucionales.', 'bi-bank2', '#f59e0b'),
    ('Comité Financiero', 'Gestión de recursos y sostenibilidad económica.', 'bi-graph-up-arrow', '#10b981'),
    ('Comité de Educación', 'Formación, capacitación y desarrollo académico en ciencia nuclear.', 'bi-mortarboard-fill', '#14b8a6'),
    ('Comité de Industria y Transporte', 'Aplicaciones industriales y transporte seguro de material nuclear.', 'bi-truck', '#e11d48'),
]


def seed(apps, schema_editor):
    Comite = apps.get_model('gestion', 'Comite')
    from django.utils.text import slugify
    for order, (name, description, icon, color) in enumerate(COMITES, start=1):
        Comite.objects.get_or_create(
            slug=slugify(name),
            defaults={
                'name': name, 'description': description,
                'icon': icon, 'color': color, 'order': order,
            },
        )


def unseed(apps, schema_editor):
    Comite = apps.get_model('gestion', 'Comite')
    from django.utils.text import slugify
    Comite.objects.filter(slug__in=[slugify(n) for n, *_ in COMITES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
