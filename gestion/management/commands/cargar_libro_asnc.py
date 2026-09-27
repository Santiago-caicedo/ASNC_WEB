"""Carga en el CRM el estado de los comités del "Libro ASNC.xlsx" (sept. 2026).

El libro es de forma libre, así que su contenido se normalizó a mano en las
estructuras de abajo. Solo intervienen usuarios registrados: cada nombre se
busca entre las cuentas de la plataforma por nombre y apellido; quien no tenga
cuenta queda mencionado en la descripción del proyecto en vez de asignarse.

Idempotente: comités por nombre, proyectos por (comité, título), tareas por
(comité, título). ``python manage.py cargar_libro_asnc [--dry-run]``.
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from gestion.models import Comite, MiembroComite, Nota, Prioridad, Proyecto, Tarea
from users.models import User

COORD, MIEMBRO = MiembroComite.Rol.COORDINADOR, MiembroComite.Rol.MIEMBRO
D = date

# Contactos internacionales del comité de relaciones estratégicas: (contacto, organización, enlace ASNC).
CONTACTOS = [
    ('Douglas Sandritge', 'Estados Unidos', 'Santiago Caicedo'),
    ('Mark Meyer', 'Generation Atomic (Estados Unidos)', 'Daniel Herrera'),
    ('Todd De Ryck', 'CNA - Canadian Nuclear Association (Canadá)', 'Daniel Herrera'),
    ('Edmanuel Torres', 'Canadá', 'Herling'),
    ('Darío Cruz', 'Unión Europea', 'Daniel Herrera'),
    ('Inaya', 'Brasil', 'Luis Eduardo Jaimes'),
    ('Pablo Hernández Arango', 'Alemania', None),
    ('INYC', 'International Nuclear Youth Congress', 'Santiago Caicedo'),
    ('LAS-ANS', 'Latin American Section - American Nuclear Society', 'Sasha'),
]

COMITES = [
    {
        'name': 'Comité de Divulgación',
        'director': 'Juan David Ortiz',
        'miembros': ['Ana María Villamizar', 'Juan José', 'Daniel Herrera', 'Catalina'],
        'nota': 'Recursos del comité: CapCut PRO.',
        'proyectos': [
            # (título, responsable, inicio, fin, avance %, descripción)
            ('Visita Marco Rubio a Colombia', None, D(2026, 9, 8), D(2026, 9, 9), 20, ''),
            ('Visita a Rio de Janeiro', None, D(2026, 8, 27), D(2026, 8, 30), 60, ''),
            ('Conferencia Semana Técnica UIS', None, D(2026, 9, 1), D(2026, 9, 2), 20, ''),
            ('Publicidad para Webinars', None, None, None, 0, ''),
            ('Webinars de Fusión', None, None, None, 0, ''),
            ('Webinars sobre tratamiento de superficies', None, None, None, 0, ''),
            ('Publicidad curso de Física', None, None, None, 0, 'Difusión del Curso introductorio en Física Nuclear (Comité de Educación).'),
        ],
    },
    {
        'name': 'Comité Científico',
        'director': 'Guillermo',
        'miembros': [],
        'proyectos': [
            ('Creación del grupo de investigación', None, None, None, 0, ''),
            ('Artículo para revista divulgativa sobre energía nuclear', None, None, None, 0, ''),
            ('Reproducir computacionalmente una celda de un reactor de potencia', None, None, None, 0, ''),
            ('Cálculo termohidráulico en reactores de potencia', None, None, None, 0, ''),
            ('Talleres de herramientas computacionales en física nuclear', None, None, None, 0, 'Talleres o seminarios para el uso de herramientas computacionales en física nuclear. Sacar piezas de divulgación.'),
            ('Colaboración con un Internet Reactor Laboratory (reactor escuela)', None, None, None, 0, ''),
            ('Contactar la escuela regional de reactores de investigación', None, None, None, 0, ''),
        ],
    },
    {
        'name': 'Comité de Regulación y Gobierno',
        'director': 'Laura Parra',
        'miembros': ['Cristian Vargas'],
        'proyectos': [
            ('Consultoría nucleoenergía CREG', 'Sasha', D(2026, 7, 1), D(2026, 8, 31), 100, 'Seguimiento en el grupo de WhatsApp del comité de regulación nuclear.'),
        ],
    },
    {
        'name': 'Comité Financiero',
        'desactivar': True,
        'nota': 'El Libro ASNC (sept. 2026) indica "Se borra": el comité queda inactivo hasta nueva decisión.',
    },
    {
        'name': 'Comité de Educación',
        'director': 'Rosa Jiménez',
        'miembros': ['Daniel Herrera', 'Leonardo Pacheco', 'Sebastián Mendoza', 'Cristian Moreno', 'Luis Eduardo Jaimes', 'Sasha'],
        'proyectos': [
            ('Curso introductorio en Física Nuclear', 'Sasha', D(2026, 9, 17), D(2026, 9, 30), 0, ''),
            ('Diplomado en energía nuclear para ACIEM', None, None, None, 0, 'Responsable: Comité Ejecutivo. Fechas por definir.'),
            ('Evento Alcaldía - UFRJ - ASNC - UNAB: capacitación de profesores', 'Rosa Jiménez', D(2026, 10, 7), D(2026, 10, 7), 0, 'Corresponsable: Luis Eduardo Jaimes.'),
            ('Programa de sensibilización nuclear nacional', 'Leonardo Pacheco', None, None, 0, 'Corresponsable: Cristian Moreno.'),
            ('Maestría UTP', 'Rosa Jiménez', D(2026, 9, 1), None, 0, 'Corresponsable: Luis Eduardo Jaimes. Fecha de cierre aún no definida.'),
            ('Maestría UNAB', 'Luis Eduardo Jaimes', None, None, 0, ''),
            ('Maestría CUC', 'Cristian Moreno', None, None, 0, ''),
        ],
    },
    {
        'name': 'Comité de Industria y Transporte',
        'director': 'Ángela Gonzáles',
        'miembros': [],
        'proyectos': [('Hoja de Ruta', None, None, None, 0, '')],
    },
    {
        'name': 'Comité de Relaciones Estratégicas',
        'crear': {'description': 'Relaciones con aliados y organizaciones nucleares internacionales.', 'order': 7},
        'director': 'Daniel Herrera',
        'miembros': [],
        'nota': 'Comité marcado con asterisco (*) en el Libro ASNC: pendiente de formalizar.',
        'proyectos': [
            ('Envío de estatutos y documentación al Dr. Sartra', 'Santiago Caicedo', None, None, 0, ''),
            ('Viaje / Evento París - Aviñón (INYC)', 'Santiago Caicedo', D(2026, 10, 5), D(2026, 10, 9), 0, 'Corresponsable: Sebastián Ardila. Relación con INYC.'),
        ],
        'contactos': True,
    },
    {
        'name': 'Comité Ejecutivo',
        'crear': {'description': 'Dirección y asuntos legales y administrativos de la Asociación.', 'order': 8},
        'director': None,
        'miembros': [],
        'proyectos': [
            ('Formalización en Cámara de Comercio', 'Santiago Caicedo', D(2026, 10, 10), None, 0, 'Pago del cambio de representante legal.'),
            ('Cobro por asociado / vinculación', None, None, None, 0, 'Responsable: Junta Directiva.'),
        ],
    },
]

SPLIT = {
    'Juan José': ('Juan José', ''), 'Juan David Ortiz': ('Juan David', 'Ortiz'),
    'Ana María Villamizar': ('Ana María', 'Villamizar'), 'Luis Eduardo Jaimes': ('Luis Eduardo', 'Jaimes'),
}


def partir(nombre):
    if nombre in SPLIT:
        return SPLIT[nombre]
    partes = nombre.split()
    return (partes[0], ' '.join(partes[1:])) if len(partes) > 1 else (partes[0], '')


class Command(BaseCommand):
    help = 'Carga en el CRM el estado de los comités del "Libro ASNC.xlsx" (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **options):
        self.dry = options['dry_run']
        self.n = {'comites': 0, 'miembros': 0, 'proyectos': 0, 'tareas': 0, 'notas': 0}
        self.sin_cuenta = set()
        self.actor = User.objects.filter(is_superuser=True).order_by('pk').first()
        with transaction.atomic():
            self.run()
            if self.dry:
                transaction.set_rollback(True)
        modo = ' (simulación, nada guardado)' if self.dry else ''
        self.stdout.write(self.style.SUCCESS(
            'Creados{}: {comites} comités, {miembros} integrantes, {proyectos} proyectos, '
            '{tareas} tareas, {notas} notas.'.format(modo, **self.n)))
        if self.sin_cuenta:
            self.stdout.write(self.style.WARNING(
                'Sin cuenta en la plataforma (quedaron mencionados en las descripciones): '
                + ', '.join(sorted(self.sin_cuenta))))

    # -- helpers --------------------------------------------------------------

    def usuario(self, nombre):
        """Usuario registrado que coincide por nombre y apellido; None si no hay."""
        if not nombre:
            return None
        first, last = partir(nombre)
        qs = User.objects.filter(is_active=True, first_name__iexact=first)
        u = qs.filter(last_name__iexact=last).first() if last else qs.first()
        if u is None:
            self.sin_cuenta.add(nombre)
        return u

    def integrante(self, comite, nombre, rol):
        u = self.usuario(nombre)
        if u is None:
            return
        m, created = MiembroComite.objects.get_or_create(comite=comite, user=u, defaults={'rol': rol})
        if created:
            self.n['miembros'] += 1
        elif rol == COORD and m.rol != COORD:
            m.rol = COORD
            m.save(update_fields=['rol'])

    def nota(self, texto, **destino):
        if not Nota.objects.filter(content=texto, **destino).exists():
            Nota.objects.create(content=texto, author=self.actor, **destino)
            self.n['notas'] += 1

    @staticmethod
    def estado(avance, inicio, fin):
        if avance >= 100:
            return Proyecto.Estado.CERRADO
        return Proyecto.Estado.ACTIVO

    # -- main -----------------------------------------------------------------

    def run(self):
        for spec in COMITES:
            comite = Comite.objects.filter(name__iexact=spec['name']).first()
            if not comite:
                if 'crear' not in spec:
                    self.stdout.write(self.style.WARNING(f'! Comité no encontrado, se omite: {spec["name"]}'))
                    continue
                comite = Comite.objects.create(name=spec['name'], **spec['crear'])
                self.n['comites'] += 1
            self.stdout.write(f'== {comite}')

            if spec.get('desactivar'):
                if comite.is_active:
                    comite.is_active = False
                    comite.save(update_fields=['is_active', 'updated_at'])
                self.nota(spec['nota'], comite=comite)
                continue

            if spec.get('director'):
                self.integrante(comite, spec['director'], COORD)
                u = self.usuario(spec['director'])
                if u and not comite.coordinator_id:
                    comite.coordinator = u
                    comite.save(update_fields=['coordinator', 'updated_at'])
            for nombre in spec.get('miembros', []):
                self.integrante(comite, nombre, MIEMBRO)
            if spec.get('nota'):
                self.nota(spec['nota'], comite=comite)

            for titulo, resp, inicio, fin, avance, desc in spec.get('proyectos', []):
                responsable = self.usuario(resp)
                partes = [desc] if desc else []
                if resp and responsable is None:
                    partes.insert(0, f'Responsable: {resp} (sin cuenta en la plataforma).')
                if 0 < avance < 100:
                    partes.append(f'Avance reportado en el Libro ASNC: {avance} %.')
                p, created = Proyecto.objects.get_or_create(
                    comite=comite, title=titulo,
                    defaults={'responsable': responsable, 'start_date': inicio, 'due_date': fin,
                              'estado': self.estado(avance, inicio, fin), 'prioridad': Prioridad.NORMAL,
                              'description': ' '.join(partes), 'created_by': self.actor},
                )
                if created:
                    self.n['proyectos'] += 1
                    self.stdout.write(f'  + {titulo}')

            if spec.get('contactos'):
                for contacto, org, enlace in CONTACTOS:
                    responsable = self.usuario(enlace)
                    desc = f'Contacto: {contacto} ({org}).'
                    if enlace and responsable is None:
                        desc += f' Enlace ASNC: {enlace} (sin cuenta en la plataforma).'
                    if not enlace:
                        desc += ' Pendiente asignar enlace ASNC.'
                    _, created = Tarea.objects.get_or_create(
                        comite=comite, title=f'Seguimiento de relación con {contacto}',
                        defaults={'asignado_a': responsable, 'description': desc,
                                  'prioridad': Prioridad.NORMAL, 'created_by': self.actor},
                    )
                    if created:
                        self.n['tareas'] += 1
