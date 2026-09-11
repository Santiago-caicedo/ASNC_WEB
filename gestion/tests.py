from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import User

from .models import Comite, MiembroComite, Nota, Persona, Proyecto, Tarea


class GestionAccessTests(TestCase):
    """Only superadmins can reach the CRM; everyone else is redirected."""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='root', email='root@asncol.com', password='x', first_name='Root', last_name='Admin',
        )
        self.admin = User.objects.create_user(
            username='admin', email='admin@asncol.com', password='x', role=User.Role.ADMIN, is_staff=True,
        )
        self.member = User.objects.create_user(username='m', email='m@asncol.com', password='x')

    def test_anonymous_redirected_to_login(self):
        r = self.client.get(reverse('gestion:home'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/acceso/', r.url)

    def test_admin_without_superuser_is_blocked(self):
        self.client.force_login(self.admin)
        for name in ('gestion:home', 'gestion:comite_list', 'gestion:persona_list',
                     'gestion:proyecto_list', 'gestion:tarea_list', 'gestion:tarea_board'):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 302, name)
            self.assertFalse(r.url.startswith('/portal/gestion'), name)

    def test_member_is_blocked_from_post_actions(self):
        self.client.force_login(self.member)
        comite = Comite.objects.first()
        r = self.client.post(reverse('gestion:nota_add', args=['comite', comite.pk]), {'content': 'hola'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(Nota.objects.count(), 0)

    def test_superuser_sees_everything(self):
        self.client.force_login(self.superuser)
        for name in ('gestion:home', 'gestion:comite_list', 'gestion:persona_list',
                     'gestion:proyecto_list', 'gestion:tarea_list', 'gestion:tarea_board',
                     'gestion:comite_create', 'gestion:persona_create',
                     'gestion:proyecto_create', 'gestion:tarea_create'):
            r = self.client.get(reverse(name))
            self.assertEqual(r.status_code, 200, name)

    def test_sidebar_section_only_for_superuser(self):
        self.client.force_login(self.admin)
        r = self.client.get('/portal/')
        self.assertNotContains(r, 'Panel CRM')
        self.client.force_login(self.superuser)
        r = self.client.get('/portal/')
        self.assertContains(r, 'Panel CRM')


class GestionFlowTests(TestCase):

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='root', email='root@asncol.com', password='x', first_name='Root', last_name='Admin',
        )
        self.client.force_login(self.superuser)
        self.comite = Comite.objects.get(slug='comite-cientifico')

    def test_seed_created_six_committees(self):
        self.assertEqual(Comite.objects.count(), 6)
        self.assertTrue(Comite.objects.filter(name='Comité de Divulgación').exists())

    def test_persona_lifecycle_and_membership(self):
        r = self.client.post(reverse('gestion:persona_create'), {
            'first_name': 'Ana', 'last_name': 'Pérez', 'tipo': 'ASOCIADO',
            'email': 'ana@example.com', 'phone': '', 'organization': 'UIS', 'position': 'Docente',
            'linkedin_url': '', 'user': '', 'notes': '', 'is_active': 'on',
        })
        persona = Persona.objects.get(email='ana@example.com')
        self.assertRedirects(r, persona.get_absolute_url())

        r = self.client.post(reverse('gestion:comite_add_member', args=[self.comite.pk]), {
            'persona': persona.pk, 'rol': 'COORDINADOR', 'joined_at': '2026-01-15', 'notes': '',
        })
        self.assertRedirects(r, self.comite.get_absolute_url())
        m = MiembroComite.objects.get(comite=self.comite, persona=persona)
        self.assertEqual(m.rol, 'COORDINADOR')

        # Adding the same person twice is rejected gracefully
        self.client.post(reverse('gestion:comite_add_member', args=[self.comite.pk]), {
            'persona': persona.pk, 'rol': 'MIEMBRO', 'joined_at': '2026-01-15',
        })
        self.assertEqual(MiembroComite.objects.filter(comite=self.comite).count(), 1)

        self.client.post(reverse('gestion:comite_update_member', args=[m.pk]), {'rol': 'SECRETARIO'})
        m.refresh_from_db()
        self.assertEqual(m.rol, 'SECRETARIO')

        r = self.client.get(self.comite.get_absolute_url())
        self.assertContains(r, 'Ana Pérez')

        self.client.post(reverse('gestion:comite_remove_member', args=[m.pk]))
        self.assertFalse(MiembroComite.objects.filter(pk=m.pk).exists())

    def test_import_users_creates_personas_once(self):
        User.objects.create_user(username='u1', email='u1@x.com', password='x', first_name='Uno', last_name='Dos')
        User.objects.create_user(username='u2', email='u2@x.com', password='x', first_name='Tres', last_name='Cuatro')
        self.client.post(reverse('gestion:persona_import'))
        self.assertEqual(Persona.objects.count(), 2)
        self.client.post(reverse('gestion:persona_import'))
        self.assertEqual(Persona.objects.count(), 2)
        # superuser itself is not imported
        self.assertFalse(Persona.objects.filter(user=self.superuser).exists())

    def test_project_and_task_flow(self):
        persona = Persona.objects.create(first_name='Luis', last_name='Gómez')
        r = self.client.post(reverse('gestion:proyecto_create'), {
            'title': 'Webinar nuclear', 'comite': self.comite.pk, 'responsable': persona.pk,
            'estado': 'EN_CURSO', 'prioridad': 'ALTA', 'start_date': '2026-09-01', 'due_date': '2026-10-01',
            'description': 'Serie de charlas',
        })
        proyecto = Proyecto.objects.get(title='Webinar nuclear')
        self.assertRedirects(r, proyecto.get_absolute_url())
        self.assertEqual(proyecto.progress, 0)

        # Task created from the project inherits its committee
        r = self.client.post(reverse('gestion:tarea_create') + f'?next={proyecto.get_absolute_url()}', {
            'title': 'Definir ponentes', 'comite': '', 'proyecto': proyecto.pk, 'asignado_a': persona.pk,
            'estado': 'PENDIENTE', 'prioridad': 'MEDIA', 'due_date': '2026-09-15', 'description': '',
            'next': proyecto.get_absolute_url(),
        })
        tarea = Tarea.objects.get(title='Definir ponentes')
        self.assertRedirects(r, proyecto.get_absolute_url())
        self.assertEqual(tarea.comite, self.comite)
        self.assertEqual(tarea.asignado_a, persona)
        proyecto.refresh_from_db()
        self.assertEqual(proyecto.tasks_total, 1)

    def test_task_overdue_and_completion(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        tarea = Tarea.objects.create(title='Vencida', comite=self.comite, due_date=yesterday)
        self.assertTrue(tarea.is_overdue)
        r = self.client.get(reverse('gestion:tarea_list') + '?estado=vencidas')
        self.assertContains(r, 'Vencida')

        self.client.post(reverse('gestion:tarea_estado', args=[tarea.pk, 'COMPLETADA']))
        tarea.refresh_from_db()
        self.assertEqual(tarea.estado, 'COMPLETADA')
        self.assertIsNotNone(tarea.completed_at)
        self.assertFalse(tarea.is_overdue)

        # Invalid state is ignored
        self.client.post(reverse('gestion:tarea_estado', args=[tarea.pk, 'LOQUESEA']))
        tarea.refresh_from_db()
        self.assertEqual(tarea.estado, 'COMPLETADA')

        # Reopening clears completed_at
        self.client.post(reverse('gestion:tarea_estado', args=[tarea.pk, 'EN_PROGRESO']))
        tarea.refresh_from_db()
        self.assertIsNone(tarea.completed_at)

    def test_project_progress(self):
        p = Proyecto.objects.create(title='P', comite=self.comite)
        Tarea.objects.create(title='a', proyecto=p, estado='COMPLETADA')
        Tarea.objects.create(title='b', proyecto=p)
        Tarea.objects.create(title='c', proyecto=p, estado='CANCELADA')
        self.assertEqual(p.progress, 50)
        r = self.client.get(p.get_absolute_url())
        self.assertContains(r, '50%')

    def test_notes_on_every_target(self):
        persona = Persona.objects.create(first_name='N')
        proyecto = Proyecto.objects.create(title='P')
        tarea = Tarea.objects.create(title='T')
        for kind, obj in (('comite', self.comite), ('persona', persona), ('proyecto', proyecto), ('tarea', tarea)):
            r = self.client.post(reverse('gestion:nota_add', args=[kind, obj.pk]), {'content': f'nota {kind}'})
            self.assertRedirects(r, obj.get_absolute_url())
        self.assertEqual(Nota.objects.count(), 4)
        nota = Nota.objects.get(tarea=tarea)
        r = self.client.post(reverse('gestion:nota_delete', args=[nota.pk]))
        self.assertRedirects(r, tarea.get_absolute_url())
        self.assertEqual(Nota.objects.count(), 3)

        # Empty note is rejected
        self.client.post(reverse('gestion:nota_add', args=['comite', self.comite.pk]), {'content': '  '})
        self.assertEqual(Nota.objects.count(), 3)

        r = self.client.get(reverse('gestion:home'))
        self.assertContains(r, 'nota comite')

    def test_delete_committee_keeps_projects_and_tasks(self):
        p = Proyecto.objects.create(title='P', comite=self.comite)
        t = Tarea.objects.create(title='T', comite=self.comite)
        self.client.post(reverse('gestion:comite_delete', args=[self.comite.pk]))
        p.refresh_from_db(); t.refresh_from_db()
        self.assertIsNone(p.comite)
        self.assertIsNone(t.comite)

    def test_persona_detail_and_filters(self):
        persona = Persona.objects.create(first_name='Filtro', last_name='Uno', tipo='ALIADO', organization='ANLA')
        MiembroComite.objects.create(comite=self.comite, persona=persona)
        r = self.client.get(reverse('gestion:persona_list') + f'?comite={self.comite.pk}&tipo=ALIADO&q=anla')
        self.assertContains(r, 'Filtro Uno')
        r = self.client.get(reverse('gestion:persona_list') + '?tipo=PROVEEDOR')
        self.assertNotContains(r, 'Filtro Uno')
        r = self.client.get(persona.get_absolute_url())
        self.assertContains(r, self.comite.name)
