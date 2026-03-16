from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_add_profile_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[
                    ('MEMBER', 'Asociado'),
                    ('NEWS_EDITOR', 'Editor de Noticias'),
                    ('ADMIN', 'Administrador'),
                ],
                db_index=True,
                default='MEMBER',
                max_length=20,
                verbose_name='Rol',
            ),
        ),
    ]
