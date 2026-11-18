"""Symposium: public landing, registration with QR ticket, attendance, certificates.

One `Simposio` row per edition; the public routes (/simposio/...) always serve
the current one (`Simposio.objects.actual()`), so next year's edition is a new
row, not new code.
"""
import datetime
import os
import re
import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

# Speaker photos are plain static files named after the speaker:
# static/images/simposio/ponentes/<slug-del-nombre>.jpg (also .jpeg, .png, .webp).
SPEAKER_PHOTOS_DIR = 'images/simposio/ponentes'
SPEAKER_PHOTO_TYPES = ('.jpg', '.jpeg', '.png', '.webp')


def speaker_photos():
    """Map of slug -> static path for every speaker photo found on disk."""
    folder = os.path.join(settings.BASE_DIR, 'static', *SPEAKER_PHOTOS_DIR.split('/'))
    try:
        names = os.listdir(folder)
    except OSError:
        return {}
    photos = {}
    for filename in sorted(names):
        stem, extension = os.path.splitext(filename)
        if extension.lower() in SPEAKER_PHOTO_TYPES:
            photos.setdefault(stem.lower(), f'{SPEAKER_PHOTOS_DIR}/{filename}')
    return photos


class SimposioQuerySet(models.QuerySet):
    def actual(self):
        """The edition served at /simposio/: the newest active one."""
        return self.filter(is_active=True).order_by('-created_at').first()


class Simposio(models.Model):
    """One edition of the symposium and everything the committee can tune."""

    title = models.CharField('Nombre', max_length=200)
    hero_kicker = models.CharField(
        'Etiqueta de la portada', max_length=60, blank=True, default='Simposio',
        help_text='Texto corto sobre el título grande. Ej: Primer simposio.',
    )
    hero_title = models.CharField(
        'Título grande de la portada', max_length=80, blank=True,
        help_text='Ej: Energía Nuclear. Si lo dejas vacío se usa el nombre.',
    )
    tagline = models.CharField(
        'Lema', max_length=250, blank=True,
        help_text='Una frase bajo el título de la página.',
    )
    description = models.TextField(
        'Presentación', blank=True,
        help_text='Texto de la sección «Sobre el simposio». Los saltos de línea se respetan.',
    )
    starts_on = models.DateField('Primer día', null=True, blank=True)
    ends_on = models.DateField(
        'Último día', null=True, blank=True,
        help_text='Déjalo vacío si dura un solo día.',
    )
    schedule_text = models.CharField(
        'Horario', max_length=120, blank=True,
        help_text='Ej: 8:00 a. m. – 5:00 p. m.',
    )
    venue = models.CharField('Lugar', max_length=200, blank=True)
    address = models.CharField('Dirección', max_length=250, blank=True)
    city = models.CharField('Ciudad', max_length=120, blank=True)
    agenda = models.TextField(
        'Programa', blank=True,
        help_text='Una línea por actividad con el formato «hora | actividad | ponente». '
                  'Una línea sin «|» se muestra como encabezado (por ejemplo, el día). '
                  'Agrega «| Aliado» al final para marcar la charla de un aliado.',
    )
    capacity = models.PositiveIntegerField(
        'Cupo', default=250,
        help_text='Al llenarse, el formulario deja de recibir inscripciones.',
    )
    is_published = models.BooleanField(
        'Página publicada', default=False,
        help_text='Sin publicar, la página solo la ven los administradores (vista previa).',
    )
    registration_open = models.BooleanField('Inscripciones abiertas', default=False)

    # Certificates
    certificates_enabled = models.BooleanField(
        'Certificados habilitados', default=False,
        help_text='Actívalo al terminar el evento: quienes asistieron podrán descargar su certificado.',
    )
    certificate_min_days = models.PositiveSmallIntegerField(
        'Días mínimos de asistencia', default=1,
        help_text='Días con asistencia registrada que se exigen para el certificado.',
    )
    certificate_hours = models.PositiveSmallIntegerField(
        'Intensidad horaria', null=True, blank=True,
        help_text='Opcional. Aparece en el certificado.',
    )
    signer_name = models.CharField('Quien firma', max_length=150, blank=True)
    signer_role = models.CharField('Cargo de quien firma', max_length=150, blank=True)

    is_active = models.BooleanField(
        'Edición vigente', default=True,
        help_text='La edición vigente más reciente es la que se muestra en /simposio/.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SimposioQuerySet.as_manager()

    class Meta:
        verbose_name = 'Simposio'
        verbose_name_plural = 'Simposios'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def last_day(self):
        return self.ends_on or self.starts_on

    @property
    def is_multiday(self):
        return bool(self.starts_on and self.ends_on and self.ends_on > self.starts_on)

    @property
    def has_ended(self):
        return bool(self.last_day and timezone.localdate() > self.last_day)

    @property
    def confirmed_count(self):
        return self.inscripciones.filter(status=Inscripcion.Status.CONFIRMED).count()

    @property
    def in_person_count(self):
        """Confirmed in-person registrations: the only ones that take a seat."""
        return self.inscripciones.filter(
            status=Inscripcion.Status.CONFIRMED, modality=Inscripcion.Modality.IN_PERSON,
        ).count()

    @property
    def seats_left(self):
        """Free seats in the auditorium (`capacity` is for in-person attendees only)."""
        return max(self.capacity - self.in_person_count, 0)

    @property
    def is_full(self):
        """No in-person seats left; virtual registrations stay open."""
        return self.seats_left == 0

    @property
    def accepts_registrations(self):
        return self.registration_open and not self.has_ended

    @property
    def sessions(self):
        """One (start, end) aware datetime pair per day of the programme.

        Day N of the agenda is `starts_on` + N; its start is the first time of
        that day and its end the last time. Used for the calendar invitations.
        """
        if not self.starts_on:
            return []

        def to_time(text):
            match = re.match(r'\s*(\d{1,2}):(\d{2})', text or '')
            if match and int(match.group(1)) < 24 and int(match.group(2)) < 60:
                return datetime.time(int(match.group(1)), int(match.group(2)))
            return None

        days = self.agenda_days or [{'items': []}]
        last = self.last_day
        sessions = []
        for index, day in enumerate(days):
            date = self.starts_on + datetime.timedelta(days=index)
            if date > last:
                break
            times = [t for item in day['items'] for t in (to_time(item['start']), to_time(item['end'])) if t]
            start = min(times) if times else datetime.time(8, 0)
            end = max(times) if times else datetime.time(17, 0)
            if end <= start:
                end = datetime.time(min(start.hour + 1, 23), start.minute)
            sessions.append((
                timezone.make_aware(datetime.datetime.combine(date, start)),
                timezone.make_aware(datetime.datetime.combine(date, end)),
            ))
        return sessions

    @property
    def hero_lines(self):
        """Cover title split in two lines; the last word goes on its own line."""
        text = (self.hero_title or self.title).strip()
        head, _, tail = text.rpartition(' ')
        return (head, tail) if head else (tail, '')

    # Words that mark an agenda row as something other than a talk.
    _BREAK_WORDS = ('café', 'cafe', 'almuerzo', 'registro', 'receso', 'espacio')

    @classmethod
    def _agenda_kind(cls, title):
        lowered = title.lower()
        if lowered.startswith(cls._BREAK_WORDS):
            return 'break'
        if lowered.startswith('panel'):
            return 'panel'
        if 'aliado' in lowered:
            return 'ally'
        if lowered.startswith(('clausura', 'instalación', 'apertura')):
            return 'ceremony'
        return 'talk'

    @staticmethod
    def _initials(name):
        words = [w for w in re.split(r'[\s.]+', name) if w]
        if not words:
            return ''
        # «Nombre Nombre Apellido Apellido»: first name and first surname.
        surname = words[2] if len(words) == 4 else words[-1]
        letters = words[0][0] + (surname[0] if len(words) > 1 else '')
        return letters.upper()

    @classmethod
    def _agenda_people(cls, speaker, kind, photos):
        """People named in the third column of an agenda line.

        Accepts «Nombre, Organización» (a talk) and
        «Ana y Luis (Org), Marta (Otra org) y Juan (Org, virtual)» (a panel).
        An organisation ending in «, virtual» flags a remote participation.
        A part after «;» that starts with «Modera:» names the moderator, e.g.
        «… ; Modera: Santiago Caicedo (Vicepresidente ejecutivo, AsNC)».
        Allies' talks name an organisation, not a person, so they give no people,
        and neither does a speaker «Por confirmar».
        """
        if not speaker or kind in ('break', 'ally'):
            return []
        # «Por confirmar» (or «Por definir») is shown as plain text, not as a person.
        if re.match(r'(?i)por\s+(confirmar|definir)\b', speaker):
            return []
        people = []
        for part in speaker.split(';'):
            part = part.strip()
            moderator = re.match(r'(?i)modera(?:dor|dora)?\s*:\s*', part)
            if moderator:
                part = part[moderator.end():]
            for name, org in cls._name_org_pairs(part):
                # «Org, virtual» (or just «virtual») marks someone who joins remotely.
                trimmed = re.sub(r'(?:^|,)\s*virtual\s*$', '', org, flags=re.IGNORECASE)
                people.append({
                    'name': name, 'org': trimmed.strip(), 'virtual': trimmed != org,
                    'moderator': bool(moderator),
                    'initials': cls._initials(name),
                    'photo': photos.get(slugify(name), ''),
                })
        return people

    @staticmethod
    def _name_org_pairs(text):
        pairs = []
        if '(' in text:
            for names, org in re.findall(r'([^()]+)\(([^)]*)\)', text):
                names = re.sub(r'^[\s,]*(?:y\s+)?', '', names)
                for name in re.split(r'\s+y\s+|,', names):
                    pairs.append((name.strip(), org.strip()))
        else:
            name, _, org = text.partition(',')
            pairs.append((name.strip(), org.strip()))
        return [(name, org) for name, org in pairs if name]

    @property
    def agenda_items(self):
        """Parse `agenda` into rows: {'heading'} or
        {'time', 'start', 'end', 'title', 'speaker', 'kind', 'people'}."""
        items = []
        photos = speaker_photos()
        for line in self.agenda.splitlines():
            line = line.strip()
            if not line:
                continue
            if '|' not in line:
                items.append({'heading': line})
                continue
            parts = [p.strip() for p in line.split('|')] + ['', '', '']
            kind = self._agenda_kind(parts[1])
            # A fourth column «Aliado» marks an ally's talk that names its speaker.
            people_kind = kind
            if parts[3].lower().startswith('aliado'):
                kind, people_kind = 'ally', 'talk'
            start, end = (re.split(r'\s*[–—-]\s*', parts[0], maxsplit=1) + [''])[:2]
            items.append({
                'time': parts[0], 'start': start or parts[0], 'end': end,
                'title': parts[1], 'speaker': parts[2], 'kind': kind,
                'people': self._agenda_people(parts[2], people_kind, photos),
            })
        return items

    @property
    def agenda_days(self):
        """Agenda grouped by heading line: [{'label', 'weekday', 'day', 'rest', 'items'}].

        A heading like «Jueves 3 de diciembre» is also split in its parts so the
        page can print the day number large.
        """
        days = []
        for item in self.agenda_items:
            if 'heading' in item:
                label = item['heading']
                match = re.match(r'^(\S+)\s+(\d{1,2})\s*(.*)$', label)
                weekday, number, rest = match.groups() if match else ('', '', '')
                days.append({
                    'label': label, 'weekday': weekday, 'day': number, 'rest': rest,
                    'items': [],
                })
                continue
            if not days:
                days.append({'label': '', 'weekday': '', 'day': '', 'rest': '', 'items': []})
            days[-1]['items'].append(item)
        return [day for day in days if day['items']]

    @property
    def speakers(self):
        """Everyone named in the programme, once each. A person who gives a talk
        and also sits on a panel is listed with the talk; `virtual` is true only
        when every one of their participations is remote."""
        found = {}
        for item in self.agenda_items:
            for person in item.get('people', ()):
                is_talk = item['kind'] == 'talk'
                known = found.get(person['name'])
                entry = known
                if known is None or (is_talk and not known['is_talk']):
                    entry = {
                        **person, 'talk': item['title'], 'is_talk': is_talk,
                        'order': known['order'] if known else len(found),
                    }
                entry['virtual'] = person['virtual'] and (known is None or known['virtual'])
                found[person['name']] = entry
        return sorted(found.values(), key=lambda person: person['order'])

    @property
    def agenda_stats(self):
        """Counts shown in the figures strip, derived from the programme itself."""
        rows = [i for i in self.agenda_items if 'heading' not in i]
        return {
            'days': len(self.agenda_days),
            'talks': sum(1 for i in rows if i['kind'] in ('talk', 'ally')),
            'panels': sum(1 for i in rows if i['kind'] == 'panel'),
        }


class Inscripcion(models.Model):
    """A person registered to one edition. Its UUID is the ticket (QR) code."""

    class Status(models.TextChoices):
        CONFIRMED = 'CONFIRMED', 'Confirmada'
        CANCELLED = 'CANCELLED', 'Cancelada'

    class AttendeeType(models.TextChoices):
        STUDENT = 'STUDENT', 'Estudiante'
        PROFESSIONAL = 'PROFESSIONAL', 'Profesional'
        ACADEMIC = 'ACADEMIC', 'Docente / Investigador'
        COMPANY = 'COMPANY', 'Empresa'
        GOVERNMENT = 'GOVERNMENT', 'Entidad pública'
        OTHER = 'OTHER', 'Otro'

    class Modality(models.TextChoices):
        IN_PERSON = 'PRESENCIAL', 'Presencial'
        VIRTUAL = 'VIRTUAL', 'Virtual'

    class DocumentType(models.TextChoices):
        CC = 'CC', 'Cédula de ciudadanía'
        CE = 'CE', 'Cédula de extranjería'
        TI = 'TI', 'Tarjeta de identidad'
        PASSPORT = 'PA', 'Pasaporte'

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    simposio = models.ForeignKey(
        Simposio, on_delete=models.CASCADE, related_name='inscripciones',
    )
    first_name = models.CharField('Nombres', max_length=100)
    last_name = models.CharField('Apellidos', max_length=100)
    modality = models.CharField(
        'Modalidad', max_length=12, choices=Modality.choices,
        default=Modality.IN_PERSON, db_index=True,
        help_text='Presencial recibe la entrada con QR; virtual, la confirmación y la información de conexión.',
    )
    # No longer asked in the form (kept for registrations made before).
    document_type = models.CharField(
        'Tipo de documento', max_length=2,
        choices=DocumentType.choices, blank=True, default='',
    )
    document_number = models.CharField('Número de documento', max_length=30, blank=True)
    email = models.EmailField('Correo electrónico')
    phone = models.CharField('Teléfono', max_length=30, blank=True)
    attendee_type = models.CharField(
        'Asiste como', max_length=20,
        choices=AttendeeType.choices, default=AttendeeType.PROFESSIONAL,
    )
    institution = models.CharField('Institución o empresa', max_length=200, blank=True)
    position = models.CharField('Profesión o cargo', max_length=150, blank=True)
    city = models.CharField('Ciudad', max_length=120, blank=True)
    accepts_data_policy = models.BooleanField('Acepta el tratamiento de datos', default=False)

    status = models.CharField(
        'Estado', max_length=20, choices=Status.choices, default=Status.CONFIRMED,
        db_index=True,
    )
    confirmation_sent_at = models.DateTimeField(null=True, blank=True)
    certificate_sent_at = models.DateTimeField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField('Inscrito el', auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['simposio', 'email'], name='simposio_inscripcion_email_unico',
            ),
        ]

    def __str__(self):
        return f'{self.full_name} ({self.email})'

    def save(self, *args, **kwargs):
        self.email = (self.email or '').strip().lower()
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def code(self):
        """Short human-readable code, for looking a ticket up by hand."""
        return str(self.uuid).split('-')[0].upper()

    @property
    def is_confirmed(self):
        return self.status == self.Status.CONFIRMED

    @property
    def is_virtual(self):
        return self.modality == self.Modality.VIRTUAL

    @property
    def days_attended(self):
        return self.asistencias.count()

    @property
    def can_get_certificate(self):
        s = self.simposio
        return (
            s.certificates_enabled
            and self.is_confirmed
            and self.days_attended >= max(s.certificate_min_days, 1)
        )

    def _absolute(self, path):
        return f"{settings.SITE_URL.rstrip('/')}{path}"

    def get_ticket_path(self):
        return reverse('simposio:entrada', kwargs={'uuid': self.uuid})

    def get_ticket_url(self):
        return self._absolute(self.get_ticket_path())

    def get_checkin_url(self):
        """What the QR encodes: opens the staff check-in page for this ticket."""
        return self._absolute(
            reverse('simposio_admin:checkin_ticket', kwargs={'uuid': self.uuid})
        )

    def get_certificate_url(self):
        return self._absolute(reverse('simposio:certificado', kwargs={'uuid': self.uuid}))

    def get_certificate_verify_url(self):
        return self._absolute(
            reverse('simposio:verificar_certificado', kwargs={'uuid': self.uuid})
        )


class Asistencia(models.Model):
    """Attendance of one registration on one day (one row per day at most)."""

    class Method(models.TextChoices):
        QR = 'QR', 'Código QR'
        MANUAL = 'MANUAL', 'Manual'

    inscripcion = models.ForeignKey(
        Inscripcion, on_delete=models.CASCADE, related_name='asistencias',
    )
    day = models.DateField('Día')
    checked_in_at = models.DateTimeField('Hora de ingreso', auto_now_add=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name='Registrada por',
    )
    method = models.CharField(max_length=10, choices=Method.choices, default=Method.QR)

    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-checked_in_at']
        constraints = [
            models.UniqueConstraint(
                fields=['inscripcion', 'day'], name='simposio_asistencia_unica_por_dia',
            ),
        ]

    def __str__(self):
        return f'{self.inscripcion.full_name} · {self.day:%d/%m/%Y}'
