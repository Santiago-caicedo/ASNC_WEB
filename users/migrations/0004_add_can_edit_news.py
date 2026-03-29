from django.db import migrations, models


def migrate_news_editors(apps, schema_editor):
    """Convert existing NEWS_EDITOR users to MEMBER with can_edit_news=True."""
    User = apps.get_model('users', 'User')
    User.objects.filter(role='NEWS_EDITOR').update(
        can_edit_news=True,
        role='MEMBER',
    )


def reverse_migration(apps, schema_editor):
    """Reverse: convert can_edit_news users back to NEWS_EDITOR role."""
    User = apps.get_model('users', 'User')
    User.objects.filter(can_edit_news=True, role='MEMBER').update(
        role='NEWS_EDITOR',
        can_edit_news=False,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_add_user_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='can_edit_news',
            field=models.BooleanField(
                default=False,
                help_text='Permite al usuario crear, editar y eliminar noticias desde el portal.',
                verbose_name='Puede gestionar noticias',
            ),
        ),
        migrations.RunPython(migrate_news_editors, reverse_migration),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(
                choices=[('MEMBER', 'Asociado'), ('ADMIN', 'Administrador')],
                db_index=True,
                default='MEMBER',
                max_length=20,
                verbose_name='Rol',
            ),
        ),
    ]
