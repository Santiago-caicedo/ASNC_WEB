import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import convocatorias.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Convocatoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('title', models.CharField(max_length=200, verbose_name='Título')),
                ('slug', models.SlugField(blank=True, max_length=230, unique=True, verbose_name='Slug')),
                ('description', models.TextField(help_text='Información visible arriba del formulario. Admite saltos de línea.', verbose_name='Descripción')),
                ('cover_image', models.ImageField(blank=True, help_text='Opcional. Se muestra arriba del título en el formulario público.', null=True, upload_to='convocatorias/', verbose_name='Imagen de portada')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activa')),
                ('opens_at', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de apertura')),
                ('closes_at', models.DateTimeField(blank=True, null=True, verbose_name='Fecha de cierre')),
                ('success_message', models.TextField(blank=True, default='¡Gracias por tu interés! Hemos recibido tu inscripción correctamente.', help_text='Texto que verá el usuario después de enviar el formulario.', verbose_name='Mensaje de confirmación')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='convocatorias_created', to=settings.AUTH_USER_MODEL, verbose_name='Creada por')),
            ],
            options={
                'verbose_name': 'Convocatoria',
                'verbose_name_plural': 'Convocatorias',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ConvocatoriaField',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('label', models.CharField(max_length=150, verbose_name='Etiqueta')),
                ('field_type', models.CharField(
                    choices=[
                        ('TEXT', 'Texto corto'),
                        ('TEXTAREA', 'Párrafo'),
                        ('EMAIL', 'Correo electrónico'),
                        ('PHONE', 'Teléfono'),
                        ('NUMBER', 'Número'),
                        ('DATE', 'Fecha'),
                        ('SELECT', 'Lista desplegable'),
                        ('CHECKBOX', 'Casilla (sí/no)'),
                        ('FILE', 'Archivo'),
                    ],
                    default='TEXT', max_length=15, verbose_name='Tipo de campo',
                )),
                ('required', models.BooleanField(default=True, verbose_name='Obligatorio')),
                ('help_text', models.CharField(blank=True, max_length=255, verbose_name='Texto de ayuda')),
                ('placeholder', models.CharField(blank=True, max_length=120, verbose_name='Placeholder')),
                ('options', models.TextField(blank=True, help_text='Solo para lista desplegable. Una opción por línea.', verbose_name='Opciones')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('convocatoria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='convocatorias.convocatoria')),
            ],
            options={
                'verbose_name': 'Campo de Convocatoria',
                'verbose_name_plural': 'Campos de Convocatoria',
                'ordering': ['order', 'pk'],
            },
        ),
        migrations.CreateModel(
            name='ConvocatoriaSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('data', models.JSONField(default=dict, help_text='Diccionario con {"label": "valor"} de cada campo.', verbose_name='Respuestas')),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('convocatoria', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='convocatorias.convocatoria')),
            ],
            options={
                'verbose_name': 'Inscripción',
                'verbose_name_plural': 'Inscripciones',
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.CreateModel(
            name='ConvocatoriaSubmissionFile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_label', models.CharField(max_length=150)),
                ('file', models.FileField(upload_to=convocatorias.models.submission_file_path)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='convocatorias.convocatoriasubmission')),
            ],
            options={
                'ordering': ['uploaded_at'],
            },
        ),
    ]
