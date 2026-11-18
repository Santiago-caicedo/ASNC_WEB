from django.db import migrations


def seed(apps, schema_editor):
    """Create the first edition, unpublished, so the committee only has to fill it in."""
    Simposio = apps.get_model('simposio', 'Simposio')
    if Simposio.objects.exists():
        return
    Simposio.objects.create(
        title='Simposio Nuclear Colombiano',
        tagline='Ciencia, tecnología y energía nuclear para el desarrollo del país.',
        capacity=250,
        is_published=False,
        registration_open=False,
    )


def unseed(apps, schema_editor):
    Simposio = apps.get_model('simposio', 'Simposio')
    Simposio.objects.filter(
        title='Simposio Nuclear Colombiano', inscripciones__isnull=True,
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('simposio', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
