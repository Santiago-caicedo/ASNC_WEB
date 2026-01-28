# Generated manually for adding profile fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, max_length=20, verbose_name='Teléfono'),
        ),
        migrations.AddField(
            model_name='user',
            name='profession',
            field=models.CharField(blank=True, max_length=100, verbose_name='Profesión / Título'),
        ),
        migrations.AddField(
            model_name='user',
            name='current_job',
            field=models.CharField(blank=True, max_length=100, verbose_name='Cargo Actual'),
        ),
        migrations.AddField(
            model_name='user',
            name='institution',
            field=models.CharField(blank=True, max_length=150, verbose_name='Empresa / Institución'),
        ),
        migrations.AddField(
            model_name='user',
            name='linkedin_url',
            field=models.URLField(blank=True, verbose_name='LinkedIn'),
        ),
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.TextField(blank=True, help_text='Breve descripción de tu trayectoria profesional', verbose_name='Biografía Profesional'),
        ),
    ]
