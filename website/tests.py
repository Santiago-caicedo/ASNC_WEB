import json

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .views import ENSO_DATA_PATH


class EnsoDataTests(TestCase):
    """Observatorio ENSO: endpoint de datos y presencia en la portada."""

    def setUp(self):
        # El endpoint cachea el archivo en memoria; se limpia entre pruebas.
        cache.delete('enso_data_json')

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
        # La sección va inmediatamente después del hero.
        self.assertLess(html.index('scroll-indicator'), html.index('id="ensoBoard"'))
        self.assertLess(html.index('id="ensoBoard"'), html.index('news-home-section'))
