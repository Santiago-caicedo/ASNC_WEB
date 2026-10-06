import json

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .views import ENSO_DATA_PATH


class EnsoDataTests(TestCase):
    """Observatorio ENSO: endpoint de datos y presencia en la portada."""

    def setUp(self):
        # El endpoint cachea el archivo en memoria; se limpia entre pruebas.
        cache.clear()

    def test_archivo_de_datos_existe_y_es_coherente(self):
        self.assertTrue(ENSO_DATA_PATH.exists(), 'Falta website/data/enso.json')
        d = json.loads(ENSO_DATA_PATH.read_text(encoding='utf-8'))
        for clave in ('meta', 'kpis', 'serie', 'episodios', 'modelo', 'pronostico'):
            self.assertIn(clave, d)

        # La serie va de 1950 en adelante y está ordenada por fecha.
        fechas = [p['f'] for p in d['serie']]
        self.assertEqual(fechas, sorted(fechas))
        self.assertTrue(fechas[0].startswith('1950'))
        self.assertEqual(len(fechas), d['meta']['n_temporadas'])

        # Todo episodio cumple la racha mínima y el umbral de la NOAA.
        umbral, racha = d['meta']['umbral'], d['meta']['racha_minima']
        for e in d['episodios']:
            self.assertGreaterEqual(e['duracion'], racha, e)
            self.assertIn(e['tipo'], ('nino', 'nina'))
            if e['tipo'] == 'nino':
                self.assertGreaterEqual(e['pico'], umbral, e)
            else:
                self.assertLessEqual(e['pico'], -umbral, e)

        # Los porcentajes por fase reparten el total.
        k = d['kpis']
        self.assertAlmostEqual(k['pct_nino'] + k['pct_nina'] + k['pct_neutral'], 100, places=0)

        # El ranking del modelo solo marca como seleccionadas las no redundantes.
        sel = set(d['modelo']['seleccionadas'])
        self.assertTrue(sel)
        for r in d['modelo']['ranking']:
            self.assertEqual(r['seleccionada'], r['feature'] in sel, r['feature'])
            if r['seleccionada']:
                self.assertTrue(r['significativa'], r['feature'])

        # La varianza acumulada del PCA no decrece y llega al 95 % donde se indica.
        pca = d['modelo']['pca']
        self.assertEqual(pca['acumulada'], sorted(pca['acumulada']))
        self.assertGreaterEqual(pca['acumulada'][pca['n_para_95'] - 1], 95)

        # Cada horizonte de pronóstico reporta su línea base para comparar.
        self.assertTrue(d['pronostico']['horizontes'])
        for h in d['pronostico']['horizontes']:
            self.assertIn('base', h)
            self.assertGreater(h['n_prueba'], 0)

    def test_endpoint_devuelve_json_cacheable(self):
        r = self.client.get(reverse('enso_data'))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/json')
        self.assertIn('max-age', r.get('Cache-Control', ''))
        self.assertEqual(len(json.loads(r.content)['serie']),
                         json.loads(r.content)['meta']['n_temporadas'])

    def test_endpoint_es_publico(self):
        # El tablero vive en la portada: no debe exigir sesión.
        self.assertEqual(self.client.get(reverse('enso_data')).status_code, 200)

    def test_portada_incluye_el_tablero(self):
        r = self.client.get(reverse('home'))
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('id="ensoBoard"', html)
        self.assertIn(reverse('enso_data'), html)
        # Marco compacto en la portada; el tablero completo vive en un diálogo.
        self.assertIn('id="ensoDialog"', html)
        self.assertIn('data-enso-open', html)
        # La sección va inmediatamente después del hero.
        self.assertLess(html.index('scroll-indicator'), html.index('id="ensoBoard"'))
        self.assertLess(html.index('id="ensoBoard"'), html.index('news-home-section'))


from datetime import timedelta

from django.utils import timezone

from users.models import User
from .models import Event


def _event(title, starts_in, hours=2, **kwargs):
    start = timezone.now() + starts_in
    kwargs.setdefault('summary', 'Resumen del evento.')
    return Event.objects.create(
        title=title, starts_at=start,
        ends_at=start + timedelta(hours=hours) if hours else None, **kwargs,
    )


class EventPublicTests(TestCase):
    """Eventos: agenda pública, detalle, calendario y recuadro de la portada."""

    def test_proximos_y_anteriores(self):
        lejano = _event('Lejano', timedelta(days=30))
        cercano = _event('Cercano', timedelta(days=3))
        en_curso = _event('En curso', timedelta(hours=-1), hours=3)
        pasado = _event('Pasado', timedelta(days=-10))
        _event('Borrador', timedelta(days=1), is_published=False)

        self.assertEqual(list(Event.objects.upcoming()), [en_curso, cercano, lejano])
        self.assertEqual(list(Event.objects.past()), [pasado])
        self.assertTrue(en_curso.is_ongoing)

    def test_sin_hora_de_fin_sigue_vigente_hasta_el_final_del_dia(self):
        hoy = timezone.localtime().replace(hour=0, minute=1, second=0, microsecond=0)
        ev = Event.objects.create(title='Hoy temprano', summary='x', starts_at=hoy)
        self.assertIn(ev, Event.objects.upcoming())
        self.assertFalse(ev.is_past)

    def test_portada_muestra_el_evento_mas_proximo(self):
        _event('Segundo', timedelta(days=20))
        _event('Primero', timedelta(days=2), registration_url='https://forms.example.com/x')
        r = self.client.get(reverse('home'), HTTP_HOST='localhost')
        self.assertEqual(r.context['next_event'].title, 'Primero')
        self.assertContains(r, 'Próximo evento')
        self.assertContains(r, 'https://forms.example.com/x')
        self.assertNotContains(r, 'Noticias de la Asociación')

    def test_portada_sin_eventos_vuelve_a_las_noticias(self):
        _event('Pasado', timedelta(days=-3))
        r = self.client.get(reverse('home'), HTTP_HOST='localhost')
        self.assertIsNone(r.context['next_event'])
        self.assertContains(r, 'Noticias de la Asociación')

    def test_agenda_detalle_y_calendario(self):
        ev = _event('Jornada de Medicina Nuclear', timedelta(days=5), location='UNAB, Bucaramanga')
        _event('Taller, parte 2', timedelta(days=40))
        r = self.client.get(reverse('events'), HTTP_HOST='localhost')
        self.assertContains(r, 'Jornada de Medicina Nuclear')
        self.assertContains(r, 'Taller, parte 2')
        self.assertNotContains(r, 'En Construcción')

        r = self.client.get(ev.get_absolute_url(), HTTP_HOST='localhost')
        self.assertContains(r, 'UNAB, Bucaramanga')

        r = self.client.get(reverse('event_ics', args=[ev.slug]), HTTP_HOST='localhost')
        self.assertEqual(r['Content-Type'], 'text/calendar; charset=utf-8')
        body = r.content.decode()
        self.assertIn('SUMMARY:Jornada de Medicina Nuclear', body)
        self.assertIn('LOCATION:UNAB\\, Bucaramanga', body)

    def test_agenda_vacia(self):
        r = self.client.get(reverse('events'), HTTP_HOST='localhost')
        self.assertContains(r, 'No hay eventos programados por ahora')

    def test_borrador_no_es_publico(self):
        ev = _event('Oculto', timedelta(days=5), is_published=False)
        r = self.client.get(ev.get_absolute_url(), HTTP_HOST='localhost')
        self.assertEqual(r.status_code, 404)


class EventPortalTests(TestCase):
    """Gestión de eventos en /portal/eventos/: solo el superadmin."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='root', email='root@asncol.com', password='x',
        )
        self.admin = User.objects.create_user(
            username='admin', email='admin@asncol.com', password='x',
            role=User.Role.ADMIN, is_staff=True,
        )

    def _post_data(self, **overrides):
        day = (timezone.localdate() + timedelta(days=10)).isoformat()
        data = {
            'title': 'Webinar de protección radiológica',
            'event_type': 'WEBINAR', 'modality': 'VIRTUAL',
            'location': 'Zoom', 'summary': 'Para profesionales del sector.',
            'description': '', 'registration_url': '',
            'date': day, 'start_time': '18:00', 'end_time': '19:30', 'end_date': '',
            'is_published': 'on',
        }
        data.update(overrides)
        return data

    def test_admin_no_superuser_no_entra(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse('event_list'), HTTP_HOST='localhost')
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('event_create'), self._post_data(), HTTP_HOST='localhost')
        self.assertEqual(r.status_code, 302)
        self.assertFalse(Event.objects.exists())

    def test_superuser_crea_edita_y_elimina(self):
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.get(reverse('event_list'), HTTP_HOST='localhost').status_code, 200)

        r = self.client.post(reverse('event_create'), self._post_data(), HTTP_HOST='localhost')
        self.assertRedirects(r, reverse('event_list'), fetch_redirect_response=False)
        ev = Event.objects.get()
        inicio = timezone.localtime(ev.starts_at)
        self.assertEqual((inicio.hour, inicio.minute), (18, 0))
        self.assertEqual(ev.ends_at - ev.starts_at, timedelta(minutes=90))
        self.assertEqual(ev.created_by, self.superuser)

        # El formulario de edición viene prellenado con fecha y horas locales.
        r = self.client.get(reverse('event_update', args=[ev.pk]), HTTP_HOST='localhost')
        self.assertContains(r, 'value="18:00"')

        r = self.client.post(
            reverse('event_update', args=[ev.pk]),
            self._post_data(title='Nuevo título', end_time=''), HTTP_HOST='localhost',
        )
        ev.refresh_from_db()
        self.assertEqual(ev.title, 'Nuevo título')
        self.assertIsNone(ev.ends_at)

        self.client.post(reverse('event_delete', args=[ev.pk]), HTTP_HOST='localhost')
        self.assertFalse(Event.objects.exists())

    def test_fin_antes_del_inicio_es_error(self):
        self.client.force_login(self.superuser)
        r = self.client.post(reverse('event_create'), self._post_data(end_time='17:00'), HTTP_HOST='localhost')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'El evento debe terminar después de empezar.')
        self.assertFalse(Event.objects.exists())
