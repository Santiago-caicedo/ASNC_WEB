from datetime import timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import User
from website.models import HeroSlide, NewsArticle, NewsCategory

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


class HeroSlideTests(TestCase):
    """Slides of the homepage carousel: managed by news editors, shown on the home."""

    def setUp(self):
        self.editor = User.objects.create_user(
            username='editor', email='editor@example.com', password='x',
            can_edit_news=True,
        )
        self.client.force_login(self.editor)

    def _post(self, **extra):
        data = {
            'title': 'Curso de protección radiológica',
            'kicker': 'Curso',
            'main_image': SimpleUploadedFile('m.gif', GIF, 'image/gif'),
            'main_style': 'PHOTO',
            'color': 'VIOLET',
            'link_url': '/eventos/',
            'is_active': 'on',
            'display_order': 0,
        }
        data.update(extra)
        return self.client.post(reverse('slide_create'), data)

    def test_editor_creates_slide_and_it_shows_on_home(self):
        response = self._post()
        self.assertRedirects(response, reverse('slide_list'))
        slide = HeroSlide.objects.get()
        self.assertEqual(slide.created_by, self.editor)

        html = self.client.get(reverse('home')).content.decode()
        self.assertIn('data-hs', html)
        self.assertIn('hs-c-violet', html)
        self.assertIn('Curso de protección radiológica', html)
        self.assertNotIn('class="hero-section"', html)

    def test_home_falls_back_to_classic_hero_without_visible_slides(self):
        self._post(is_active='')
        self._post(show_until=(timezone.localdate() - timedelta(days=1)).isoformat())
        self.assertEqual(HeroSlide.objects.count(), 2)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['hero_slides'], [])
        self.assertIn('class="hero-section"', response.content.decode())

    def test_show_until_includes_that_day(self):
        self._post(show_until=timezone.localdate().isoformat())
        self.assertEqual(HeroSlide.objects.visible().count(), 1)

    def test_rejects_unsafe_link(self):
        for bad in ('javascript:alert(1)', '//evil.com', 'evil.com'):
            response = self._post(link_url=bad)
            self.assertEqual(response.status_code, 200)
            self.assertIn('link_url', response.context['form'].errors)
        self.assertFalse(HeroSlide.objects.exists())

    def test_regular_member_cannot_manage_slides(self):
        member = User.objects.create_user(username='m', email='m@example.com', password='x')
        self.client.force_login(member)
        self.assertRedirects(self.client.get(reverse('slide_list')), '/mi-portal/', fetch_redirect_response=False)

    def test_clear_secondary_image(self):
        self._post(secondary_image=SimpleUploadedFile('s.gif', GIF, 'image/gif'))
        slide = HeroSlide.objects.get()
        self.assertTrue(slide.secondary_image)
        data = {
            'title': slide.title, 'main_style': 'PHOTO', 'color': 'TEAL',
            'display_order': 0, 'is_active': 'on', 'secondary_image-clear': 'on',
        }
        response = self.client.post(reverse('slide_update', args=[slide.pk]), data)
        self.assertRedirects(response, reverse('slide_list'))
        slide.refresh_from_db()
        self.assertFalse(slide.secondary_image)
        self.assertTrue(slide.main_image)
