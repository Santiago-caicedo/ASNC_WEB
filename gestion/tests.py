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
        self.assertNotIn('ana@x.com</option>', html[idx:idx + 4000])
        self.assertIn('luis@x.com</option>', html[idx:idx + 4000])

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
        self.assertEqual((t.comite, t.proyecto, t.asignado_a), (self.comite, p, self.ana))

        self.client.post(reverse('gestion:tarea_estado', args=[t.pk]), {'estado': 'COMPLETADA'})
        t.refresh_from_db()
        self.assertTrue(t.is_done)
        self.assertIsNotNone(t.completed_at)
        # Completada: desaparece de la vista por defecto y vuelve con ?todas=1.
        self.assertNotContains(self.client.get(self.url), 'Definir ponentes')
        self.assertContains(self.client.get(self.url + '&todas=1'), 'Definir ponentes')

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
        self.assertNotContains(self.client.get(self.url), 'Curso')
        self.client.post(reverse('gestion:proyecto_delete', args=[p.pk]))
        self.assertEqual(Tarea.objects.filter(title='a').count(), 0)

    def test_vista_general_agrupa_y_marca_vencidas(self):
        ayer = timezone.localdate() - timedelta(days=1)
        Tarea.objects.create(title='Vencida', comite=self.comite, due_date=ayer)
        Tarea.objects.create(title='Suelta', comite=None)
        r = self.client.get(reverse('gestion:workspace'))
        html = r.content.decode()
        self.assertIn('Vencidas', html)
        self.assertLess(html.index('Vencida'), html.index('Suelta'))
        self.assertIn('Sin comité', html)
        # Badge del menú lateral.
        self.assertEqual(r.context['gestion_vencidas'], 1)

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
