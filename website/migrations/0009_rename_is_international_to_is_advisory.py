from django.db import migrations, models

import website.countries


class Migration(migrations.Migration):
    """El Comité Asesor deja de ser solo internacional.

    `is_international` significaba en realidad "pertenece al Comité Asesor", y
    ahora ese comité tiene una rama nacional, así que el nombre pasaba a ser
    engañoso. El país es el que decide la rama: Colombia -> nacional.
    """

    dependencies = [
        ('website', '0008_featuredmember_country_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='featuredmember',
            old_name='is_international',
            new_name='is_advisory',
        ),
        migrations.AlterField(
            model_name='featuredmember',
            name='is_advisory',
            field=models.BooleanField(
                default=False,
                help_text='Marcar si hace parte del Comité Asesor',
                verbose_name='Comité Asesor',
            ),
        ),
        migrations.AlterField(
            model_name='featuredmember',
            name='country',
            field=models.CharField(
                blank=True,
                choices=website.countries.COUNTRIES,
                help_text=(
                    'País del miembro del Comité Asesor (se muestra con su bandera). '
                    'Colombia lo ubica en el comité nacional; cualquier otro país, en el internacional.'
                ),
                max_length=2,
                verbose_name='País',
            ),
        ),
    ]
