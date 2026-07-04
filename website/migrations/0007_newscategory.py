from django.db import migrations, models
import django.db.models.deletion


# Mapeo de las categorías fijas anteriores hacia las nuevas categorías-modelo.
LEGACY_CATEGORIES = {
    'ASSOCIATION': ('De la Asociación', 'de-la-asociacion', 1),
    'NUCLEAR': ('Temática Nuclear', 'tematica-nuclear', 2),
}


def create_categories_and_migrate(apps, schema_editor):
    """Crea una NewsCategory por cada categoría fija existente y reasigna
    cada noticia a la categoría correspondiente según su valor anterior."""
    NewsCategory = apps.get_model('website', 'NewsCategory')
    NewsArticle = apps.get_model('website', 'NewsArticle')

    code_to_category = {}
    for code, (name, slug, order) in LEGACY_CATEGORIES.items():
        category, _ = NewsCategory.objects.get_or_create(
            slug=slug,
            defaults={'name': name, 'display_order': order, 'is_active': True},
        )
        code_to_category[code] = category

    # Categoría de respaldo por si algún artículo tuviera un valor inesperado.
    fallback = code_to_category.get('NUCLEAR')

    for article in NewsArticle.objects.all():
        category = code_to_category.get(article.category_old, fallback)
        article.category = category
        article.save(update_fields=['category'])


def reverse_migrate(apps, schema_editor):
    """Restaura el valor de texto anterior a partir de la categoría-modelo."""
    NewsArticle = apps.get_model('website', 'NewsArticle')
    slug_to_code = {slug: code for code, (_, slug, _) in LEGACY_CATEGORIES.items()}
    for article in NewsArticle.objects.all():
        if article.category and article.category.slug in slug_to_code:
            article.category_old = slug_to_code[article.category.slug]
        else:
            article.category_old = 'NUCLEAR'
        article.save(update_fields=['category_old'])


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0006_contactmessage'),
    ]

    operations = [
        # 1. Crear el modelo de categorías.
        migrations.CreateModel(
            name='NewsCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Nombre')),
                ('slug', models.SlugField(blank=True, max_length=120, unique=True, verbose_name='Slug')),
                ('description', models.CharField(blank=True, help_text='Texto opcional que se muestra en la página de la categoría', max_length=200, verbose_name='Descripción')),
                ('is_active', models.BooleanField(default=True, verbose_name='Activa')),
                ('display_order', models.PositiveIntegerField(default=0, verbose_name='Orden')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Categoría de Noticia',
                'verbose_name_plural': 'Categorías de Noticias',
                'ordering': ['display_order', 'name'],
            },
        ),
        # 2. Renombrar el campo de texto viejo para conservar su dato durante la migración.
        migrations.RenameField(
            model_name='newsarticle',
            old_name='category',
            new_name='category_old',
        ),
        # 3. Añadir la nueva FK (nullable de momento).
        migrations.AddField(
            model_name='newsarticle',
            name='category',
            field=models.ForeignKey(
                help_text='Categoría a la que pertenece la noticia',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='articles',
                to='website.newscategory',
                verbose_name='Categoría',
            ),
        ),
        # 4. Crear categorías y reasignar noticias.
        migrations.RunPython(create_categories_and_migrate, reverse_migrate),
        # 5. Eliminar el campo de texto viejo.
        migrations.RemoveField(
            model_name='newsarticle',
            name='category_old',
        ),
    ]
