"""Load the committee status reported in "Libro ASNC.xlsx" (Sept 2026) into the CRM.

The workbook is free-form, so its content was normalised by hand into the
structures below. The command is idempotent: people are matched by full name,
committees by name, projects by (committee, title), tasks by (committee, title).
Run it with ``python manage.py cargar_libro_asnc`` (add ``--dry-run`` to preview).
"""
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from gestion.models import Comite, MiembroComite, Nota, Persona, Prioridad, Proyecto, Tarea
from users.models import User

ASOCIADO, ALIADO, INSTITUCION = Persona.Tipo.ASOCIADO, Persona.Tipo.ALIADO, Persona.Tipo.INSTITUCION
COORD, MIEMBRO, COLAB = MiembroComite.Rol.COORDINADOR, MiembroComite.Rol.MIEMBRO, MiembroComite.Rol.COLABORADOR

# ---------------------------------------------------------------------------
# People (ASNC). Key = canonical full name as it will appear in the CRM.
# ---------------------------------------------------------------------------
PERSONAS = {
    'Juan David Ortiz': {},
    'Ana María Villamizar': {},
    'Juan José': {'notes': 'Apellido pendiente de confirmar (Libro ASNC).'},
    'Daniel Herrera': {},
    'Catalina': {'notes': 'Apellido pendiente de confirmar (Libro ASNC).'},
    'Guillermo': {'notes': 'Apellido pendiente de confirmar (Libro ASNC).'},
    'Laura Parra': {},
    'Cristian Vargas': {},
    'Sasha': {'notes': 'Apellido pendiente de confirmar (Libro ASNC).'},
    'Rosa Jiménez': {},
    'Leonardo Pacheco': {},
    'Sebastián Mendoza': {},
    'Cristian Moreno': {},
    'Luis Eduardo Jaimes': {},
    'Ángela Gonzáles': {},
    'Santiago Caicedo': {},
    'Sebastián Ardila': {},
    'Herling': {'notes': 'Apellido pendiente de confirmar (Libro ASNC).'},
}

# External contacts handled by the strategic-relations committee.
CONTACTOS = [
    # (name, tipo, organization, enlace ASNC)
    ('Douglas Sandritge', ALIADO, 'Estados Unidos', 'Santiago Caicedo'),
    ('Mark Meyer', ALIADO, 'Generation Atomic (Estados Unidos)', 'Daniel Herrera'),
    ('Todd De Ryck', ALIADO, 'CNA - Canadian Nuclear Association (Canadá)', 'Daniel Herrera'),
    ('Edmanuel Torres', ALIADO, 'Canadá', 'Herling'),
    ('Darío Cruz', ALIADO, 'Unión Europea', 'Daniel Herrera'),
    ('Inaya', ALIADO, 'Brasil', 'Luis Eduardo Jaimes'),
    ('Pablo Hernández Arango', ALIADO, 'Alemania', None),
    ('INYC', INSTITUCION, 'International Nuclear Youth Congress', 'Santiago Caicedo'),
    ('LAS-ANS', INSTITUCION, 'Latin American Section - American Nuclear Society', 'Sasha'),
]
# Extra co-responsible per contact (model supports one assignee; the rest go in the description).
CONTACTO_EXTRA = {'Todd De Ryck': 'Sebastián Ardila'}

# ---------------------------------------------------------------------------
# Committees: director, members, resources, activities.
# ---------------------------------------------------------------------------
D = date
COMITES = [
    {
        'name': 'Comité de Divulgación',
        'director': 'Juan David Ortiz',
        'miembros': ['Ana María Villamizar', 'Juan José', 'Daniel Herrera', 'Catalina'],
        'recursos': 'CapCut PRO',
        'proyectos': [
            # (title, responsable, start, end, avance, extra description)
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
            ('Artículo para revista divulgativa sobre energía nuclear', None, None, None, 0, 'Publicar un artículo de divulgación acerca de la energía nuclear.'),
            ('Reproducir computacionalmente una celda de un reactor de potencia', None, None, None, 0, ''),
            ('Cálculo termohidráulico en reactores de potencia', None, None, None, 0, ''),
            ('Talleres de herramientas computacionales en física nuclear', None, None, None, 0, 'Talleres o seminarios para el uso de herramientas computacionales en física nuclear. Sacar piezas de divulgación.'),
            ('Colaboración con un Internet Reactor Laboratory (reactor escuela)', None, None, None, 0, 'Explorar la colaboración con un reactor laboratorio remoto.'),
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
            ('Diplomado en energía nuclear para ACIEM', None, None, None, 0, 'Responsable: Comité Ejecutivo. Fechas por definir (TBD).'),
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
        'proyectos': [
            ('Hoja de Ruta', None, None, None, 0, ''),
        ],
    },
    {
        'name': 'Comité de Relaciones Estratégicas',
        'crear': {'description': 'Relaciones con aliados y organizaciones nucleares internacionales.', 'icon': 'bi-globe-americas', 'color': '#6366f1', 'order': 7},
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
        'crear': {'description': 'Dirección y asuntos legales y administrativos de la Asociación.', 'icon': 'bi-briefcase-fill', 'color': '#1B2A41', 'order': 8},
        'director': None,
        'miembros': [],
        'proyectos': [
            ('Formalización en Cámara de Comercio', 'Santiago Caicedo', D(2026, 10, 10), None, 0, 'Pago del cambio de representante legal.'),
            ('Cobro por asociado / vinculación', None, None, None, 0, 'Responsable: Junta Directiva.'),
        ],
    },
]


# Names whose first/last split is not "first word / rest".
SPLIT_OVERRIDES = {
    'Juan José': ('Juan José', ''),
    'Juan David Ortiz': ('Juan David', 'Ortiz'),
    'Ana María Villamizar': ('Ana María', 'Villamizar'),
    'Luis Eduardo Jaimes': ('Luis Eduardo', 'Jaimes'),
    'Pablo Hernández Arango': ('Pablo', 'Hernández Arango'),
}


def split_name(full):
    if full in SPLIT_OVERRIDES:
        return SPLIT_OVERRIDES[full]
    parts = full.split()
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], ' '.join(parts[1:])


class Command(BaseCommand):
    help = 'Carga en el CRM el estado de los comités reportado en "Libro ASNC.xlsx" (idempotente).'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Muestra lo que haría sin guardar nada.')

    def handle(self, *args, **options):
        self.dry = options['dry_run']
        self.stats = {'personas': 0, 'comites': 0, 'miembros': 0, 'proyectos': 0, 'tareas': 0, 'notas': 0}
        self.actor = User.objects.filter(is_superuser=True).order_by('pk').first()
        with transaction.atomic():
            self.run()
            if self.dry:
                transaction.set_rollback(True)
        mode = ' (simulación, nada guardado)' if self.dry else ''
        self.stdout.write(self.style.SUCCESS(
            'Creados{}: {personas} personas, {comites} comités, {miembros} membresías, '
            '{proyectos} proyectos, {tareas} tareas, {notas} notas.'.format(mode, **self.stats)
        ))

    # -- helpers ------------------------------------------------------------

    def persona(self, full_name, tipo=ASOCIADO, organization='', notes=''):
        first, last = split_name(full_name)
        p = Persona.objects.filter(first_name__iexact=first, last_name__iexact=last).first()
        if p:
            return p
        user = None
        if tipo == ASOCIADO and last:
            user = User.objects.filter(
                first_name__iexact=first, last_name__iexact=last, persona_crm__isnull=True
            ).first()
        p = Persona.objects.create(
            first_name=first, last_name=last, tipo=tipo, organization=organization, notes=notes,
            user=user, email=user.email if user else '', phone=user.phone if user else '',
            created_by=self.actor,
        )
        self.stats['personas'] += 1
        self.log(f'  + persona {p} [{p.get_tipo_display()}]' + (f' (vinculada a {user.email})' if user else ''))
        return p

    def membresia(self, comite, persona, rol, notes=''):
        m, created = MiembroComite.objects.get_or_create(
            comite=comite, persona=persona, defaults={'rol': rol, 'notes': notes},
        )
        if created:
            self.stats['miembros'] += 1
        elif rol == COORD and m.rol != COORD:
            m.rol = COORD
            m.save(update_fields=['rol'])
        return m

    def nota(self, content, **target):
        if Nota.objects.filter(content=content, **target).exists():
            return
        Nota.objects.create(content=content, author=self.actor, **target)
        self.stats['notas'] += 1

    def log(self, msg):
        self.stdout.write(msg)

    @staticmethod
    def estado_proyecto(avance, start, end):
        today = timezone.localdate()
        if avance >= 100:
            return Proyecto.Estado.COMPLETADO
        if avance > 0 or (start and start <= today):
            return Proyecto.Estado.EN_CURSO
        if start or end:
            return Proyecto.Estado.PLANEACION
        return Proyecto.Estado.IDEA

    # -- main ----------------------------------------------------------------

    def run(self):
        for name, extra in PERSONAS.items():
            self.persona(name, **extra)

        for spec in COMITES:
            comite = Comite.objects.filter(name__iexact=spec['name']).first()
            if not comite:
                if 'crear' not in spec:
                    self.log(self.style.WARNING(f'! Comité no encontrado, se omite: {spec["name"]}'))
                    continue
                comite = Comite.objects.create(name=spec['name'], **spec['crear'])
                self.stats['comites'] += 1
                self.log(f'+ comité nuevo: {comite}')
            self.log(f'== {comite}')

            if spec.get('desactivar'):
                if comite.is_active:
                    comite.is_active = False
                    comite.save(update_fields=['is_active', 'updated_at'])
                    self.log('  - marcado como inactivo')
                self.nota(spec['nota'], comite=comite)
                continue

            if spec.get('director'):
                director = self.persona(spec['director'])
                self.membresia(comite, director, COORD)
                if director.user_id and not comite.coordinator_id:
                    comite.coordinator = director.user
                    comite.save(update_fields=['coordinator', 'updated_at'])
            for nombre in spec.get('miembros', []):
                self.membresia(comite, self.persona(nombre), MIEMBRO)

            if spec.get('recursos'):
                self.nota(f'Recursos del comité: {spec["recursos"]}', comite=comite)
            if spec.get('nota'):
                self.nota(spec['nota'], comite=comite)

            for title, resp, start, end, avance, desc in spec.get('proyectos', []):
                proyecto, created = Proyecto.objects.get_or_create(
                    comite=comite, title=title,
                    defaults={
                        'responsable': self.persona(resp) if resp else None,
                        'start_date': start, 'due_date': end, 'avance': avance,
                        'estado': self.estado_proyecto(avance, start, end),
                        'prioridad': Prioridad.MEDIA,
                        'description': desc, 'created_by': self.actor,
                    },
                )
                if created:
                    self.stats['proyectos'] += 1
                    self.log(f'  + proyecto: {title} [{proyecto.get_estado_display()}, {avance}%]')
                    self.nota('Cargado desde Libro ASNC (sept. 2026).', proyecto=proyecto)

            if spec.get('contactos'):
                self.contactos(comite)

    def contactos(self, comite):
        for name, tipo, org, enlace in CONTACTOS:
            contacto = self.persona(name, tipo=tipo, organization=org)
            self.membresia(comite, contacto, COLAB, notes=f'Enlace ASNC: {enlace}' if enlace else 'Sin enlace asignado')
            responsable = self.persona(enlace) if enlace else None
            title = f'Seguimiento de relación con {name}'
            desc = f'Contacto: {name} ({org}).'
            if name in CONTACTO_EXTRA:
                desc += f' Corresponsable: {CONTACTO_EXTRA[name]}.'
            if not enlace:
                desc += ' Pendiente asignar enlace ASNC.'
            tarea, created = Tarea.objects.get_or_create(
                comite=comite, title=title,
                defaults={
                    'asignado_a': responsable, 'description': desc,
                    'prioridad': Prioridad.MEDIA, 'created_by': self.actor,
                },
            )
            if created:
                self.stats['tareas'] += 1
                self.log(f'  + tarea: {title} -> {responsable or "sin asignar"}')
