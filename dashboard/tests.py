from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from users.models import User
from website.models import NewsArticle, NewsCategory

# 1x1 GIF, enough for the ImageField validation
GIF = (b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04'
       b'\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;')


class NewsPublishButtonsTests(TestCase):
    """A news editor who is a regular member can save drafts and publish."""

    def setUp(self):
        self.editor = User.objects.create_user(
            username='editor', email='editor@example.com', password='x',
            can_edit_news=True,
        )
        self.client.force_login(self.editor)
        self.category = NewsCategory.objects.create(name='Categoría de prueba')

    def _data(self, accion, **extra):
        data = {
            'category': self.category.pk,
            'title': 'Noticia de prueba',
            'excerpt': 'Resumen',
            'content': '<p>Contenido</p>',
            'accion': accion,
        }
        data.update(extra)
        return data

    def _create(self, accion):
        data = self._data(accion, cover_image=SimpleUploadedFile('c.gif', GIF, 'image/gif'))
        return self.client.post(reverse('news_create'), data)

    def test_form_shows_both_buttons(self):
        html = self.client.get(reverse('news_create')).content.decode()
        self.assertIn('value="borrador"', html)
        self.assertIn('value="publicar"', html)

    def test_publicar_publishes(self):
        response = self._create('publicar')
        self.assertRedirects(response, reverse('news_list'))
        article = NewsArticle.objects.get()
        self.assertTrue(article.is_published)
        self.assertIsNotNone(article.published_at)

    def test_borrador_saves_draft(self):
        self._create('borrador')
        self.assertFalse(NewsArticle.objects.get().is_published)

    def test_pasar_a_borrador_unpublishes(self):
        self._create('publicar')
        article = NewsArticle.objects.get()
        self.client.post(reverse('news_update', args=[article.pk]), self._data('borrador'))
        article.refresh_from_db()
        self.assertFalse(article.is_published)
