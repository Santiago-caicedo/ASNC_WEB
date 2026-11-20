import json
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.signing import TimestampSigner
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from users.models import User

from .models import Asistencia, Inscripcion, Simposio
from .utils import check_in, extract_ticket_uuid, format_event_dates, send_certificate_emails


def abrir(simposio, **extra):
    """Publish the edition and open registrations, with today as an event day."""
    today = timezone.localdate()
    values = {
        'is_published': True, 'registration_open': True,
        'starts_on': today, 'ends_on': today + timedelta(days=1),
        'venue': 'Auditorio', 'city': 'Bucaramanga',
    }
    values.update(extra)
    for key, value in values.items():
        setattr(simposio, key, value)
    simposio.save()
    return simposio


def datos(**extra):
    values = {
        'first_name': 'María', 'last_name': 'González', 'modality': 'PRESENCIAL',
        'email': 'maria@example.com',
        'phone': '+57 300 1234567', 'attendee_type': 'PROFESSIONAL',
        'institution': 'UIS', 'position': 'Ingeniera', 'city': 'Bucaramanga',
        'accepts_data_policy': 'on', 'website': '',
    }
    values.update(extra)
    return values


def token_viejo():
    """A form token signed 10 s ago, as if a human had filled the form."""
    with patch('time.time', return_value=timezone.now().timestamp() - 10):
        return TimestampSigner().sign('simposio')


def inscribir(simposio, **extra):
    values = {
        'first_name': 'Ana', 'last_name': 'Ruiz', 'document_number': '123456',
        'email': 'ana@example.com',
    }
    values.update(extra)
    return Inscripcion.objects.create(simposio=simposio, **values)


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.simposio = Simposio.objects.actual()  # seeded by migration 0002
        self.admin = User.objects.create_user(
            username='admin', email='admin@asncol.com', password='x',
            role=User.Role.ADMIN, is_staff=True,
        )
        self.staff = User.objects.create_user(
            username='staff', email='staff@asncol.com', password='x', is_staff=True,
        )
        self.member = User.objects.create_user(
            username='socio', email='socio@asncol.com', password='x',
        )


class PaginaPublicaTests(Base):
    def test_og_image_no_repite_el_dominio_con_static_en_s3(self):
        from django.test import override_settings
        self.simposio.is_published = True
        self.simposio.save()
        s3 = 'https://bucket.s3.amazonaws.com/asnc/static/'
        with override_settings(STATIC_URL=s3):
            html = self.client.get(reverse('simposio:landing')).content.decode()
        self.assertIn(f'<meta property="og:image" content="{s3}images/og-image.png">', html)
        self.assertIn(f'<meta name="twitter:image" content="{s3}images/og-image.png">', html)
        self.assertNotIn('asncol.comhttp', html)

    def test_la_migracion_crea_la_edicion_sin_publicar(self):
        self.assertIsNotNone(self.simposio)
        self.assertFalse(self.simposio.is_published)

    def test_sin_publicar_solo_la_ven_los_administradores(self):
        url = reverse('simposio:landing')
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Vista previa')

    def test_publicada_muestra_datos_y_programa(self):
        abrir(
            self.simposio,
            agenda='Día 1\n8:00 | Registro |\n9:00 | Fusión | Dra. Pérez\nDía 2\n9:00 | Panel 1 | Varios',
        )
        response = self.client.get(reverse('simposio:landing'))
        self.assertContains(response, 'Inscribirme gratis')
        self.assertContains(response, 'Dra. Pérez')
        self.assertContains(response, 'Auditorio')
        self.assertContains(response, 'role="tab"', count=2)
        self.assertContains(response, 'T08:00:00-05:00')  # countdown starts at the first session
        self.assertEqual(self.simposio.agenda_stats, {'days': 2, 'talks': 1, 'panels': 1})

    def test_la_migracion_carga_el_contenido_de_2026(self):
        s = self.simposio
        self.assertEqual(s.title, 'Primer Simposio de Energía Nuclear')
        self.assertEqual(s.hero_lines, ('Energía', 'Nuclear'))
        self.assertEqual(format_event_dates(s), '3 y 4 de diciembre de 2026')
        self.assertEqual(s.agenda_stats, {'days': 2, 'talks': 11, 'panels': 2})
        kinds = {i['title']: i['kind'] for i in s.agenda_items if 'kind' in i}
        self.assertEqual(kinds['Café'], 'break')
        self.assertEqual(kinds['Charla de aliado institucional'], 'ally')
        self.assertEqual(kinds['Clausura'], 'ceremony')

    def test_formato_de_fechas(self):
        s = self.simposio
        s.starts_on = timezone.datetime(2027, 3, 12).date()
        s.ends_on = None
        self.assertEqual(format_event_dates(s), '12 de marzo de 2027')
        s.ends_on = timezone.datetime(2027, 3, 14).date()
        self.assertEqual(format_event_dates(s), 'del 12 al 14 de marzo de 2027')
        s.ends_on = timezone.datetime(2027, 4, 1).date()
        self.assertEqual(format_event_dates(s), 'del 12 de marzo al 1 de abril de 2027')


class InscripcionTests(Base):
    def setUp(self):
        super().setUp()
        abrir(self.simposio)
        self.url = reverse('simposio:registro')

    def post(self, **extra):
        return self.client.post(self.url, datos(form_token=token_viejo(), **extra))

    def test_inscripcion_crea_registro_y_envia_la_entrada(self):
        response = self.post()
        self.assertRedirects(response, reverse('simposio:gracias'))
        inscripcion = Inscripcion.objects.get()
        self.assertEqual(inscripcion.email, 'maria@example.com')
        self.assertIsNotNone(inscripcion.confirmation_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['maria@example.com'])
        self.assertIn('Registro presencial', message.subject)
        self.assertIn('registro presencial', message.alternatives[0][0])
        self.assertIn(str(inscripcion.uuid), message.alternatives[0][0])
        self.assertEqual(message.attachments[0][0], 'entrada-qr.png')
        self.assertIn('simposio.ics', [attachment[0] for attachment in message.attachments])
        # Thanks page offers the ticket
        self.assertContains(self.client.get(reverse('simposio:gracias')), inscripcion.get_ticket_path())

    def test_correo_repetido_no_duplica_ni_muestra_la_entrada(self):
        self.post()
        other = self.client_class()
        response = other.post(self.url, datos(form_token=token_viejo(), email='MARIA@example.com'))
        self.assertRedirects(response, reverse('simposio:gracias'))
        self.assertEqual(Inscripcion.objects.count(), 1)
        thanks = other.get(reverse('simposio:gracias'))
        self.assertContains(thanks, 'ya estaba inscrito')
        self.assertNotContains(thanks, str(Inscripcion.objects.get().uuid))

    def test_envio_instantaneo_o_sin_token_se_rechaza(self):
        fast = self.client.post(self.url, datos(form_token=TimestampSigner().sign('simposio')))
        self.assertEqual(fast.status_code, 200)
        missing = self.client.post(self.url, datos())
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(Inscripcion.objects.count(), 0)

    def test_honeypot_y_politica_de_datos(self):
        self.assertEqual(self.post(website='http://spam').status_code, 200)
        self.assertEqual(self.post(accepts_data_policy='').status_code, 200)
        self.assertEqual(Inscripcion.objects.count(), 0)

    def test_cupo_presencial_agotado_deja_inscribirse_en_virtual(self):
        self.simposio.capacity = 1
        self.simposio.save()
        inscribir(self.simposio)
        self.assertContains(self.client.get(self.url), 'Cupos presenciales agotados')
        response = self.post()
        self.assertContains(response, 'Se agotaron los cupos presenciales')
        self.assertEqual(Inscripcion.objects.count(), 1)
        response = self.post(modality='VIRTUAL')
        self.assertRedirects(response, reverse('simposio:gracias'))
        self.assertEqual(Inscripcion.objects.filter(modality='VIRTUAL').count(), 1)

    def test_inscripcion_virtual_recibe_confirmacion_y_calendario(self):
        response = self.post(modality='VIRTUAL')
        self.assertRedirects(response, reverse('simposio:gracias'))
        inscripcion = Inscripcion.objects.get()
        self.assertTrue(inscripcion.is_virtual)
        message = mail.outbox[0]
        self.assertIn('virtual', message.subject.lower())
        names = [attachment[0] for attachment in message.attachments]
        self.assertNotIn('entrada-qr.png', names)
        self.assertIn('simposio.ics', names)
        html = message.alternatives[0][0]
        self.assertIn('calendar.google.com', html)
        self.assertIn('información de conexión', html)
        thanks = self.client.get(reverse('simposio:gracias'))
        self.assertContains(thanks, 'inscripción virtual está completa')
        ticket = self.client.get(inscripcion.get_ticket_path())
        self.assertNotContains(ticket, 'Código QR de tu entrada')
        ics = self.client.get(reverse('simposio:entrada_ics', args=[inscripcion.uuid]))
        self.assertEqual(ics['Content-Type'], 'text/calendar; charset=utf-8')
        self.assertEqual(ics.content.decode().count('BEGIN:VEVENT'), len(self.simposio.sessions))

    def test_el_formulario_ya_no_pide_documento(self):
        page = self.client.get(self.url)
        self.assertNotContains(page, 'document_number')
        self.assertContains(page, 'name="modality"')

    def test_inscripciones_cerradas(self):
        self.simposio.registration_open = False
        self.simposio.save()
        self.assertContains(self.client.get(self.url), 'Inscripciones próximamente')
        self.post()
        self.assertEqual(Inscripcion.objects.count(), 0)

    def test_fallo_del_correo_no_pierde_la_inscripcion(self):
        with patch('simposio.views.send_confirmation_email', side_effect=RuntimeError('smtp')):
            response = self.post()
        self.assertRedirects(response, reverse('simposio:gracias'))
        self.assertEqual(Inscripcion.objects.count(), 1)


class EntradaTests(Base):
    def setUp(self):
        super().setUp()
        abrir(self.simposio)
        self.inscripcion = inscribir(self.simposio)

    def test_entrada_muestra_el_qr(self):
        response = self.client.get(self.inscripcion.get_ticket_path())
        self.assertContains(response, 'data:image/png;base64,')
        self.assertContains(response, self.inscripcion.code)

    def test_qr_png(self):
        response = self.client.get(reverse('simposio:entrada_qr', args=[self.inscripcion.uuid]))
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(response.content.startswith(b'\x89PNG'))

    def test_entrada_cancelada_no_tiene_qr(self):
        self.inscripcion.status = Inscripcion.Status.CANCELLED
        self.inscripcion.save()
        response = self.client.get(self.inscripcion.get_ticket_path())
        self.assertNotContains(response, 'data:image/png;base64,')
        qr = self.client.get(reverse('simposio:entrada_qr', args=[self.inscripcion.uuid]))
        self.assertEqual(qr.status_code, 404)


class AsistenciaTests(Base):
    def setUp(self):
        super().setUp()
        abrir(self.simposio)
        self.inscripcion = inscribir(self.simposio)
        self.api = reverse('simposio_admin:checkin_api')

    def scan(self, code):
        return self.client.post(self.api, json.dumps({'code': code}), content_type='application/json')

    def test_el_qr_lleva_el_uuid(self):
        self.assertEqual(extract_ticket_uuid(self.inscripcion.get_checkin_url()), self.inscripcion.uuid)
        self.assertIsNone(extract_ticket_uuid('hola'))

    def test_escanear_requiere_personal(self):
        self.assertEqual(self.scan(str(self.inscripcion.uuid)).status_code, 302)
        self.client.force_login(self.member)
        self.assertEqual(self.scan(str(self.inscripcion.uuid)).status_code, 302)
        self.assertEqual(Asistencia.objects.count(), 0)

    def test_escaneo_registra_una_sola_vez_por_dia(self):
        self.client.force_login(self.staff)
        first = self.scan(self.inscripcion.get_checkin_url()).json()
        self.assertEqual(first['code'], 'ok')
        self.assertEqual(first['name'], 'Ana Ruiz')
        self.assertEqual(first['attended_today'], 1)
        second = self.scan(str(self.inscripcion.uuid)).json()
        self.assertEqual(second['code'], 'repeated')
        self.assertEqual(Asistencia.objects.count(), 1)

    def test_codigo_desconocido_y_cancelada(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.scan('00000000-0000-0000-0000-000000000000').json()['code'], 'unknown')
        self.inscripcion.status = Inscripcion.Status.CANCELLED
        self.inscripcion.save()
        self.assertEqual(self.scan(str(self.inscripcion.uuid)).json()['code'], 'cancelled')
        self.assertEqual(Asistencia.objects.count(), 0)

    def test_fuera_de_las_fechas_no_registra(self):
        today = timezone.localdate()
        abrir(self.simposio, starts_on=today + timedelta(days=5), ends_on=None)
        ok, code, _, _ = check_in(Inscripcion.objects.get(pk=self.inscripcion.pk))
        self.assertFalse(ok)
        self.assertEqual(code, 'not_today')

    def test_pagina_del_qr_solo_registra_con_post(self):
        url = reverse('simposio_admin:checkin_ticket', args=[self.inscripcion.uuid])
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        self.assertContains(self.client.get(url), 'Registrar asistencia de hoy')
        self.assertEqual(Asistencia.objects.count(), 0)
        self.assertContains(self.client.post(url), 'Asistencia registrada')
        self.assertEqual(Asistencia.objects.count(), 1)

    def test_la_camara_solo_se_permite_en_el_escaner(self):
        self.client.force_login(self.staff)
        scanner = self.client.get(reverse('simposio_admin:escanear'))
        self.assertEqual(scanner.status_code, 200)
        self.assertIn('camera=(self)', scanner['Permissions-Policy'])
        self.assertIn('camera=()', self.client.get(reverse('simposio:landing'))['Permissions-Policy'])


class PortalTests(Base):
    def setUp(self):
        super().setUp()
        abrir(self.simposio)
        self.inscripcion = inscribir(self.simposio)

    def test_gestion_solo_para_administradores(self):
        url = reverse('simposio_admin:list')
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(
            self.client.post(reverse('simposio_admin:inscripcion_estado', args=[self.inscripcion.pk])).status_code,
            302,
        )
        self.inscripcion.refresh_from_db()
        self.assertTrue(self.inscripcion.is_confirmed)

    def test_lista_filtros_y_acciones(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('simposio_admin:list'), {'q': 'ana'})
        self.assertContains(response, 'Ana Ruiz')
        self.assertContains(response, 'Simposio')  # sidebar link
        self.assertNotContains(
            self.client.get(reverse('simposio_admin:list'), {'estado': 'asistieron'}), 'Ana Ruiz',
        )

        self.client.post(reverse('simposio_admin:asistencia_manual', args=[self.inscripcion.pk]))
        self.assertEqual(self.inscripcion.asistencias.get().method, Asistencia.Method.MANUAL)
        self.client.post(reverse('simposio_admin:asistencia_quitar', args=[self.inscripcion.pk]))
        self.assertEqual(self.inscripcion.asistencias.count(), 0)

        self.client.post(reverse('simposio_admin:inscripcion_estado', args=[self.inscripcion.pk]))
        self.inscripcion.refresh_from_db()
        self.assertFalse(self.inscripcion.is_confirmed)
        self.assertEqual(self.simposio.confirmed_count, 0)

    def test_reenviar_entrada(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('simposio_admin:reenviar', args=[self.inscripcion.pk]))
        self.assertEqual(len(mail.outbox), 1)

    def test_configuracion(self):
        self.client.force_login(self.admin)
        url = reverse('simposio_admin:config')
        self.assertEqual(self.client.get(url).status_code, 200)
        data = {
            'title': 'I Simposio Nuclear', 'tagline': '', 'description': 'Texto',
            'starts_on': '2027-03-12', 'ends_on': '2027-03-11', 'schedule_text': '',
            'venue': '', 'address': '', 'city': '', 'agenda': '',
            'capacity': 250, 'is_published': 'on', 'registration_open': 'on',
            'certificate_min_days': 1, 'certificate_hours': '',
            'signer_name': '', 'signer_role': '',
        }
        self.assertEqual(self.client.post(url, data).status_code, 200)  # end before start
        data['ends_on'] = '2027-03-13'
        self.assertRedirects(self.client.post(url, data), url)
        self.simposio.refresh_from_db()
        self.assertEqual(self.simposio.title, 'I Simposio Nuclear')
        self.assertTrue(self.simposio.is_multiday)

    def test_exportar_excel(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('simposio_admin:export_excel'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.content.startswith(b'PK'))


class CertificadoTests(Base):
    def setUp(self):
        super().setUp()
        abrir(self.simposio, signer_name='Presidente ASNC', signer_role='Presidente', certificate_hours=16)
        self.asistio = inscribir(self.simposio)
        self.ausente = inscribir(self.simposio, email='luis@example.com', first_name='Luis')
        check_in(self.asistio)

    def test_no_disponible_hasta_habilitarlos(self):
        response = self.client.get(reverse('simposio:certificado', args=[self.asistio.uuid]))
        self.assertRedirects(response, self.asistio.get_ticket_path())
        verify = self.client.get(reverse('simposio:verificar_certificado', args=[self.asistio.uuid]))
        self.assertContains(verify, 'No hay un certificado válido')

    def test_pdf_solo_para_quien_asistio(self):
        self.simposio.certificates_enabled = True
        self.simposio.save()
        response = self.client.get(reverse('simposio:certificado', args=[self.asistio.uuid]))
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        absent = self.client.get(reverse('simposio:certificado', args=[self.ausente.uuid]))
        self.assertEqual(absent.status_code, 302)

        verify = self.client.get(reverse('simposio:verificar_certificado', args=[self.asistio.uuid]))
        self.assertContains(verify, 'Certificado válido')
        self.assertNotContains(verify, self.asistio.document_number)  # masked
        self.assertContains(self.client.get(self.asistio.get_ticket_path()), 'Descargar certificado')

    def test_minimo_de_dias(self):
        self.simposio.certificates_enabled = True
        self.simposio.certificate_min_days = 2
        self.simposio.save()
        self.assertFalse(Inscripcion.objects.get(pk=self.asistio.pk).can_get_certificate)

    def test_envio_por_lotes_sin_repetir(self):
        self.simposio.certificates_enabled = True
        self.simposio.save()
        sent, failed, remaining = send_certificate_emails(self.simposio)
        self.assertEqual((sent, failed, remaining), (1, 0, 0))
        self.assertEqual(mail.outbox[0].to, ['ana@example.com'])
        self.assertEqual(send_certificate_emails(self.simposio), (0, 0, 0))

        self.client.force_login(self.admin)
        self.client.post(reverse('simposio_admin:enviar_certificados'))
        self.assertEqual(len(mail.outbox), 1)


class AgendaPeopleTests(SimpleTestCase):
    """Speakers are read from the third column of each agenda line."""

    AGENDA = (
        'Jueves 3 de diciembre\n'
        '8:30 – 9:05 | Radiación | Jhon Aponte, QA Positron\n'
        '9:40 – 10:00 | Café |\n'
        '11:10 – 11:30 | Charla de aliado institucional | International Nuclear Industry (INI)\n'
        '15:00 – 16:15 | Panel 1. Transición | Ana Ruiz y Luis Paz (UA), Darío Cruz (Fusenet) y Jhon Aponte (QA, virtual)\n'
    )

    def test_talks_and_panels_give_people(self):
        day = Simposio(agenda=self.AGENDA).agenda_days[0]
        self.assertEqual((day['weekday'], day['day'], day['rest']), ('Jueves', '3', 'de diciembre'))
        talk, coffee, ally, panel = day['items']
        self.assertEqual((talk['start'], talk['end']), ('8:30', '9:05'))
        self.assertEqual(
            [(p['name'], p['org'], p['initials']) for p in talk['people']],
            [('Jhon Aponte', 'QA Positron', 'JA')],
        )
        self.assertEqual(coffee['people'], [])
        self.assertEqual(ally['people'], [])
        self.assertEqual(
            [(p['name'], p['org']) for p in panel['people']],
            [('Ana Ruiz', 'UA'), ('Luis Paz', 'UA'), ('Darío Cruz', 'Fusenet'), ('Jhon Aponte', 'QA')],
        )
        self.assertEqual([p['virtual'] for p in panel['people']], [False, False, False, True])

    def test_speakers_are_listed_once_with_their_talk(self):
        speakers = Simposio(agenda=self.AGENDA).speakers
        self.assertEqual([s['name'] for s in speakers], ['Jhon Aponte', 'Ana Ruiz', 'Luis Paz', 'Darío Cruz'])
        self.assertEqual(speakers[0]['talk'], 'Radiación')
        # In person for the talk, remote for the panel: not a virtual speaker.
        self.assertFalse(speakers[0]['virtual'])

    def test_speaker_to_be_confirmed_is_not_a_person(self):
        agenda = 'Jueves 3 de diciembre\n8:30 – 9:05 | Radiación | Por confirmar\n'
        simposio = Simposio(agenda=agenda)
        item = simposio.agenda_items[1]
        self.assertEqual((item['speaker'], item['people']), ('Por confirmar', []))
        self.assertEqual(simposio.speakers, [])

    def test_speakers_grid_puts_listed_people_first(self):
        agenda = (
            'Jueves 3 de diciembre\n'
            '8:30 – 9:05 | Uno | Ana Ruiz, UA\n'
            '9:05 – 9:40 | Dos | Karen Ibarra, WiN\n'
            '9:40 – 10:15 | Tres | Rafael Fragozo, UPME\n'
            '10:15 – 10:50 | Cuatro | Lourdes Meriño, UA\n'
            '10:50 – 11:25 | Cinco | Pedro Gil, UA\n'
        )
        names = [s['name'] for s in Simposio(agenda=agenda).speakers_grid]
        self.assertEqual(names[:2], ['Rafael Fragozo', 'Karen Ibarra'])
        self.assertEqual(sorted(names[2:4]), ['Ana Ruiz', 'Pedro Gil'])
        self.assertEqual(names[-1], 'Lourdes Meriño')

    def test_participation_marked_with_asterisk_is_tentative(self):
        agenda = (
            'Jueves 3 de diciembre\n'
            '15:00 – 16:15 | Panel 1 | Ana Ruiz (UA) y Carlos Cárdenas* (ACIEM, virtual)\n'
        )
        simposio = Simposio(agenda=agenda)
        ana, carlos = simposio.agenda_items[1]['people']
        self.assertEqual((carlos['name'], carlos['tentative'], carlos['virtual']), ('Carlos Cárdenas', True, True))
        self.assertFalse(ana['tentative'])
        self.assertTrue(simposio.has_tentative)
        self.assertFalse(Simposio(agenda=agenda.replace('*', '')).has_tentative)

    def test_moderator(self):
        agenda = (
            'Jueves 3 de diciembre\n'
            '15:00 – 16:15 | Panel 1 | Ana Ruiz (UA) y Luis Paz (UPME); Modera: Santiago Caicedo (Vicepresidente ejecutivo, AsNC)\n'
        )
        simposio = Simposio(agenda=agenda)
        people = simposio.agenda_items[1]['people']
        self.assertEqual(
            [(p['name'], p['org'], p['moderator']) for p in people],
            [('Ana Ruiz', 'UA', False), ('Luis Paz', 'UPME', False),
             ('Santiago Caicedo', 'Vicepresidente ejecutivo, AsNC', True)],
        )
        self.assertEqual(simposio.speakers[-1]['talk'], 'Panel 1')

    def test_ally_talk_with_speaker(self):
        agenda = 'Viernes 4 de diciembre\n8:35 – 8:55 | El rol del oficial | Carlos Vega | Aliado\n'
        item = Simposio(agenda=agenda).agenda_items[1]
        self.assertEqual(item['kind'], 'ally')
        self.assertEqual([(p['name'], p['org']) for p in item['people']], [('Carlos Vega', '')])

    def test_virtual_speaker(self):
        agenda = (
            'Viernes 4 de diciembre\n'
            '9:50 – 10:25 | Fusión | Darío Cruz, CEO de Fusenet, virtual\n'
            '10:25 – 11:45 | Panel 2 | Darío Cruz (CEO de Fusenet, virtual)\n'
        )
        speaker, = Simposio(agenda=agenda).speakers
        self.assertEqual((speaker['org'], speaker['virtual']), ('CEO de Fusenet', True))
