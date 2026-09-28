from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import User

from .models import Comite, MiembroComite, Nota, Proyecto, Tarea


def crear_super():
    return User.objects.create_superuser(
        username='root', email='root@asncol.com', password='x', first_name='Root', last_name='Admin',
    )


class AccesoTests(TestCase):
    """Solo superadministradores; el resto es redirigido, también en los POST."""

    def setUp(self):
        self.su = crear_super()
        self.admin = User.objects.create_user(
            username='admin', email='admin@asncol.com', password='x', role=User.Role.ADMIN, is_staff=True,
        )
        self.comite = Comite.objects.first()

    def test_anonimo_va_al_login(self):
        r = self.client.get(reverse('gestion:workspace'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/acceso/', r.url)

    def test_admin_sin_superusuario_bloqueado(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('gestion:workspace')).status_code, 302)
        r = self.client.post(reverse('gestion:nota_add', args=['comite', self.comite.pk]), {'content': 'x'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Nota.objects.count(), 0)

    def test_superusuario_entra_y_ve_el_menu(self):
        self.client.force_login(self.su)
        self.assertEqual(self.client.get(reverse('gestion:workspace')).status_code, 200)
        self.assertEqual(self.client.get(reverse('gestion:workspace') + f'?comite={self.comite.pk}').status_code, 200)
        self.assertContains(self.client.get('/portal/'), 'Gestión de comités')
        self.client.force_login(self.admin)
        self.assertNotContains(self.client.get('/portal/'), 'Gestión de comités')


class FlujoTests(TestCase):

    def setUp(self):
        self.su = crear_super()
        self.client.force_login(self.su)
        self.comite = Comite.objects.get(slug='comite-cientifico')
        self.ana = User.objects.create_user(username='ana', email='ana@x.com', password='x', first_name='Ana', last_name='Pérez')
        self.luis = User.objects.create_user(username='luis', email='luis@x.com', password='x', first_name='Luis', last_name='Gómez')
        self.url = reverse('gestion:workspace') + f'?comite={self.comite.pk}'

    def test_semilla_de_comites(self):
        self.assertEqual(Comite.objects.count(), 6)

    def test_integrantes_solo_usuarios_registrados(self):
        r = self.client.post(reverse('gestion:miembro_add', args=[self.comite.pk]), {'user': self.ana.pk, 'rol': 'COORDINADOR'})
        self.assertRedirects(r, self.url)
        m = MiembroComite.objects.get(comite=self.comite, user=self.ana)
        self.assertEqual(m.rol, 'COORDINADOR')

        # Repetido: no se duplica.
        self.client.post(reverse('gestion:miembro_add', args=[self.comite.pk]), {'user': self.ana.pk, 'rol': 'MIEMBRO'})
        self.assertEqual(MiembroComite.objects.filter(comite=self.comite).count(), 1)

        # Solo aparecen en el selector quienes aún no son integrantes.
        html = self.client.get(self.url).content.decode()
        self.assertIn('Ana Pérez', html)
        idx = html.index('Añadir integrante…')
        self.assertNotIn('>Ana Pérez</option>', html[idx:idx + 1500])
        self.assertIn('>Luis Gómez</option>', html[idx:idx + 1500])

        self.client.post(reverse('gestion:miembro_rol', args=[m.pk]), {'rol': 'MIEMBRO'})
        m.refresh_from_db()
        self.assertEqual(m.rol, 'MIEMBRO')
        self.client.post(reverse('gestion:miembro_remove', args=[m.pk]))
        self.assertFalse(MiembroComite.objects.filter(pk=m.pk).exists())

    def test_alta_rapida_de_tarea_y_completar(self):
        p = Proyecto.objects.create(title='Webinar', comite=self.comite, created_by=self.su)
        r = self.client.post(reverse('gestion:tarea_quick'), {
            'title': 'Definir ponentes', 'comite': self.comite.pk, 'proyecto': p.pk,
            'asignado_a': self.ana.pk, 'due_date': '2026-10-15', 'next': self.url,
        })
        self.assertRedirects(r, self.url)
        t = Tarea.objects.get(title='Definir ponentes')
        self.assertEqual((t.comite, t.proyecto, t.asignado_a, t.prioridad), (self.comite, p, self.ana, 'NORMAL'))
        # Prioridad alta desde el compositor.
        self.client.post(reverse('gestion:tarea_quick'), {'title': 'Urgente', 'comite': self.comite.pk, 'alta': '1'})
        self.assertEqual(Tarea.objects.get(title='Urgente').prioridad, 'ALTA')

        self.client.post(reverse('gestion:tarea_estado', args=[t.pk]), {'estado': 'COMPLETADA'})
        t.refresh_from_db()
        self.assertTrue(t.is_done)
        self.assertIsNotNone(t.completed_at)
        # Completada: sale de los horizontes y pasa al desplegable de cerradas.
        r = self.client.get(self.url)
        abiertas = [x.title for _, _, _, lista in r.context['horizontes'] for x in lista]
        self.assertEqual(abiertas, ['Urgente'])
        self.assertEqual([x.pk for x in r.context['cerradas']], [t.pk])

        self.client.post(reverse('gestion:tarea_estado', args=[t.pk]), {'estado': 'PENDIENTE'})
        t.refresh_from_db()
        self.assertIsNone(t.completed_at)
        self.client.post(reverse('gestion:tarea_estado', args=[t.pk]), {'estado': 'INVENTADO'})
        t.refresh_from_db()
        self.assertEqual(t.estado, 'PENDIENTE')

    def test_editar_tarea_desde_el_modal(self):
        t = Tarea.objects.create(title='Vieja', comite=self.comite)
        r = self.client.post(reverse('gestion:tarea_update', args=[t.pk]), {
            'title': 'Nueva', 'comite': self.comite.pk, 'proyecto': '', 'asignado_a': self.luis.pk,
            'estado': 'EN_PROGRESO', 'prioridad': 'ALTA', 'due_date': '', 'description': 'detalle',
        })
        self.assertRedirects(r, self.url)
        t.refresh_from_db()
        self.assertEqual((t.title, t.asignado_a, t.estado, t.prioridad), ('Nueva', self.luis, 'EN_PROGRESO', 'ALTA'))
        self.client.post(reverse('gestion:tarea_delete', args=[t.pk]))
        self.assertFalse(Tarea.objects.filter(pk=t.pk).exists())

    def test_proyecto_crear_estado_y_eliminar_con_tareas(self):
        r = self.client.post(reverse('gestion:proyecto_create'), {
            'title': 'Curso', 'comite': self.comite.pk, 'responsable': self.ana.pk, 'estado': 'ACTIVO',
            'prioridad': 'NORMAL', 'start_date': '2026-10-01', 'due_date': '2026-09-01', 'description': '',
        })
        self.assertEqual(Proyecto.objects.filter(title='Curso').count(), 0)  # fecha objetivo anterior al inicio
        self.client.post(reverse('gestion:proyecto_create'), {
            'title': 'Curso', 'comite': self.comite.pk, 'responsable': self.ana.pk, 'estado': 'ACTIVO',
            'prioridad': 'NORMAL', 'start_date': '2026-09-01', 'due_date': '2026-10-01', 'description': '',
        })
        p = Proyecto.objects.get(title='Curso')
        Tarea.objects.create(title='a', proyecto=p)
        self.client.post(reverse('gestion:proyecto_estado', args=[p.pk]), {'estado': 'CERRADO'})
        p.refresh_from_db()
        self.assertEqual(p.estado, 'CERRADO')
        # Cerrado: sale de las tarjetas activas y pasa al desplegable de cerrados.
        r = self.client.get(self.url)
        self.assertNotIn(p, r.context['proyectos'])
        self.assertIn(p, r.context['proyectos_cerrados'])
        self.client.post(reverse('gestion:proyecto_delete', args=[p.pk]))
        self.assertEqual(Tarea.objects.filter(title='a').count(), 0)

    def test_horizontes_y_resumen(self):
        hoy = timezone.localdate()
        Tarea.objects.create(title='Vencida', comite=self.comite, due_date=hoy - timedelta(days=1))
        Tarea.objects.create(title='De hoy', comite=self.comite, due_date=hoy)
        Tarea.objects.create(title='Semana', comite=self.comite, due_date=hoy + timedelta(days=5))
        Tarea.objects.create(title='Luego', comite=self.comite, due_date=hoy + timedelta(days=30))
        Tarea.objects.create(title='Suelta', comite=None)
        r = self.client.get(reverse('gestion:workspace'))
        claves = [h[0] for h in r.context['horizontes']]
        self.assertEqual(claves, ['vencidas', 'hoy', 'semana', 'luego', 'sin_fecha'])
        self.assertEqual(r.context['resumen'], {'abiertas': 5, 'vencidas': 1, 'semana': 2, 'sin_responsable': 5})
        self.assertEqual(r.context['gestion_vencidas'], 1)  # badge del menú
        titulos = [t.title for _, _, _, lista in r.context['horizontes'] for t in lista]
        self.assertEqual(titulos, ['Vencida', 'De hoy', 'Semana', 'Luego', 'Suelta'])

    def test_seleccionar_proyecto_filtra_las_tareas(self):
        p = Proyecto.objects.create(title='Webinar', comite=self.comite)
        q = Proyecto.objects.create(title='Otro', comite=self.comite)
        Tarea.objects.create(title='Del webinar', proyecto=p)
        Tarea.objects.create(title='Del otro', proyecto=q, estado='COMPLETADA')
        Tarea.objects.create(title='Sin proyecto', comite=self.comite)
        r = self.client.get(self.url + f'&proyecto={p.pk}')
        self.assertEqual(r.context['proyecto_sel'], p)
        titulos = [t.title for _, _, _, lista in r.context['horizontes'] for t in lista]
        self.assertEqual(titulos, ['Del webinar'])
        # Anillo: hechas/total por proyecto.
        avance = {x.title: (x.hechas, x.total) for x in r.context['proyectos']}
        self.assertEqual(avance, {'Webinar': (0, 1), 'Otro': (1, 1)})
        self.assertContains(r, 'de Webinar')  # filtro visible en el título de Tareas

    def test_notas_en_comite_proyecto_y_tarea(self):
        p = Proyecto.objects.create(title='P', comite=self.comite)
        t = Tarea.objects.create(title='T', comite=self.comite)
        for kind, obj in (('comite', self.comite), ('proyecto', p), ('tarea', t)):
            r = self.client.post(reverse('gestion:nota_add', args=[kind, obj.pk]), {'content': f'nota {kind}'})
            self.assertRedirects(r, self.url)
        self.assertEqual(Nota.objects.count(), 3)
        self.client.post(reverse('gestion:nota_add', args=['comite', self.comite.pk]), {'content': ' '})
        self.assertEqual(Nota.objects.count(), 3)
        n = Nota.objects.get(tarea=t)
        self.client.post(reverse('gestion:nota_delete', args=[n.pk]))
        self.assertEqual(Nota.objects.count(), 2)

    def test_comite_crear_editar_y_eliminar_conserva_trabajo(self):
        self.client.post(reverse('gestion:comite_create'), {
            'name': 'Comité Nuevo', 'description': 'x', 'coordinator': self.ana.pk, 'is_active': 'on', 'order': 9,
        })
        c = Comite.objects.get(name='Comité Nuevo')
        self.assertEqual(c.coordinator, self.ana)
        self.client.post(reverse('gestion:comite_update', args=[c.pk]), {
            'name': 'Comité Renombrado', 'description': '', 'coordinator': '', 'order': 9,
        })
        c.refresh_from_db()
        self.assertEqual((c.name, c.is_active), ('Comité Renombrado', False))
        p = Proyecto.objects.create(title='P', comite=c)
        t = Tarea.objects.create(title='T', comite=c)
        self.client.post(reverse('gestion:comite_delete', args=[c.pk]))
        p.refresh_from_db(); t.refresh_from_db()
        self.assertIsNone(p.comite)
        self.assertIsNone(t.comite)
