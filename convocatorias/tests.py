from django.test import TestCase
from django.urls import reverse

from users.models import User

from .models import Convocatoria, ConvocatoriaField, ConvocatoriaSubmission


class CollectEmailsTests(TestCase):
    """Botón "Copiar correos" del listado de inscripciones."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='root', email='root@asncol.com', password='x',
            first_name='Root', last_name='Admin',
        )
        self.conv = Convocatoria.objects.create(title='Curso de física nuclear', created_by=self.admin)
        ConvocatoriaField.objects.create(convocatoria=self.conv, label='Nombre', field_type='TEXT', order=1)
        ConvocatoriaField.objects.create(convocatoria=self.conv, label='Correo', field_type='EMAIL', order=2)
        self.url = reverse('convocatorias_admin:submissions', args=[self.conv.pk])

    def inscribir(self, **data):
        return ConvocatoriaSubmission.objects.create(convocatoria=self.conv, data=data)

    def test_recolecta_sin_duplicados_y_en_orden(self):
        self.inscribir(Nombre='Ana', Correo='ana@example.com')
        self.inscribir(Nombre='Luis', Correo=' LUIS@example.com ')
        self.inscribir(Nombre='Ana otra vez', Correo='Ana@Example.com')   # repetido, distinto uso de mayúsculas
        self.inscribir(Nombre='Sin correo', Correo='')
        self.inscribir(Nombre='Mal escrito', Correo='no-es-un-correo')
        self.assertEqual(self.conv.collect_emails(), ['ana@example.com', 'LUIS@example.com'])

    def test_acepta_correos_escritos_en_campos_de_texto(self):
        # El formulario pudo pedir el correo en un campo TEXT: también cuenta.
        self.inscribir(Nombre='carlos@example.com', Correo='')
        self.assertEqual(self.conv.collect_emails(), ['carlos@example.com'])

    def test_listado_muestra_los_correos_separados_por_comas(self):
        self.inscribir(Nombre='Ana', Correo='ana@example.com')
        self.inscribir(Nombre='Luis', Correo='luis@example.com')
        self.client.force_login(self.admin)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['emails_joined'], 'ana@example.com, luis@example.com')
        self.assertContains(r, 'id="emailsModal"')
        self.assertContains(r, 'ana@example.com, luis@example.com')

    def test_sin_correos_el_boton_queda_deshabilitado(self):
        self.inscribir(Nombre='Sin correo', Correo='')
        self.client.force_login(self.admin)
        r = self.client.get(self.url)
        self.assertEqual(r.context['emails'], [])
        self.assertNotContains(r, 'id="emailsModal"')
        self.assertContains(r, 'data-bs-target="#emailsModal" disabled')

    def test_solo_administradores(self):
        miembro = User.objects.create_user(username='m', email='m@asncol.com', password='x')
        self.client.force_login(miembro)
        self.assertEqual(self.client.get(self.url).status_code, 302)
