"""QR tickets, attendance, e-mails and the attendance certificate (PDF)."""
import base64
import datetime
import io
import logging
import re
import uuid as uuid_lib
from email.utils import formataddr
from urllib.parse import urlencode

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.html import strip_tags

from carnets.utils import generate_qr_code

from .models import Asistencia, Inscripcion, Simposio

logger = logging.getLogger(__name__)

UUID_RE = re.compile(
    r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', re.IGNORECASE,
)


# ---------------------------------------------------------------- QR ticket

def ticket_qr_png(inscripcion, size=600):
    """PNG bytes of the ticket QR (encodes the staff check-in URL)."""
    image = generate_qr_code(inscripcion.get_checkin_url(), size=size)
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


def ticket_qr_data_uri(inscripcion, size=420):
    encoded = base64.b64encode(ticket_qr_png(inscripcion, size=size)).decode('ascii')
    return f'data:image/png;base64,{encoded}'


def extract_ticket_uuid(text):
    """Pull the ticket UUID out of whatever the scanner read (URL or bare code)."""
    match = UUID_RE.search(text or '')
    if not match:
        return None
    try:
        return uuid_lib.UUID(match.group(0))
    except ValueError:
        return None


# ---------------------------------------------------------------- Attendance

def check_in(inscripcion, user=None, method=Asistencia.Method.QR):
    """Register today's attendance for a ticket.

    Returns (ok, code, message, asistencia). `code` is one of:
    'ok', 'repeated', 'cancelled', 'not_today'.
    """
    simposio = inscripcion.simposio
    today = timezone.localdate()

    if inscripcion.is_waitlisted:
        return (
            False, 'waitlist',
            'Esta persona está en la lista de espera: todavía no tiene cupo presencial.',
            None,
        )
    if not inscripcion.is_confirmed:
        return False, 'cancelled', 'Esta inscripción está cancelada.', None

    if simposio.starts_on and not (simposio.starts_on <= today <= simposio.last_day):
        return (
            False, 'not_today',
            'La entrada es válida, pero hoy no es un día del simposio: no se registró asistencia.',
            None,
        )

    try:
        with transaction.atomic():
            asistencia, created = Asistencia.objects.get_or_create(
                inscripcion=inscripcion, day=today,
                defaults={'checked_in_by': user, 'method': method},
            )
    except IntegrityError:
        # Two scanners read the same ticket at once: the other one won.
        asistencia = Asistencia.objects.get(inscripcion=inscripcion, day=today)
        created = False

    if created:
        return True, 'ok', 'Asistencia registrada.', asistencia

    hora = date_format(timezone.localtime(asistencia.checked_in_at), 'g:i a')
    return True, 'repeated', f'Ya había ingresado hoy a las {hora}.', asistencia


# ---------------------------------------------------------------- E-mails

def _from_email():
    return formataddr(('Asociación Nuclear Colombiana', settings.DEFAULT_FROM_EMAIL))


# ---------------------------------------------------------------- Calendar

def _ics_escape(text):
    return (
        str(text or '').replace('\\', '\\\\').replace(';', '\\;')
        .replace(',', '\\,').replace('\n', '\\n')
    )


def _event_location(simposio, virtual=False):
    place = ', '.join(p for p in (simposio.venue, simposio.address, simposio.city) if p)
    return 'Virtual (el enlace llegará por correo)' if virtual else place


def calendar_ics(simposio, virtual=False):
    """An .ics with one event per day of the symposium."""
    fmt = '%Y%m%dT%H%M%SZ'
    utc = datetime.timezone.utc
    site = settings.SITE_URL.rstrip('/')
    url = f"{site}{simposio_landing_path()}"
    description = (
        'Participación virtual: te enviaremos el enlace de conexión por correo antes del evento.'
        if virtual else 'Lleva tu entrada con el código QR para registrar tu asistencia.'
    )
    lines = [
        'BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//ASNC//Simposio//ES',
        'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
    ]
    stamp = timezone.now().astimezone(utc).strftime(fmt)
    for number, (start, end) in enumerate(simposio.sessions, start=1):
        lines += [
            'BEGIN:VEVENT',
            f'UID:simposio-{simposio.pk}-dia-{number}@asncol.com',
            f'DTSTAMP:{stamp}',
            f'DTSTART:{start.astimezone(utc).strftime(fmt)}',
            f'DTEND:{end.astimezone(utc).strftime(fmt)}',
            f'SUMMARY:{_ics_escape(simposio.title)} (día {number})',
            f'DESCRIPTION:{_ics_escape(description + chr(10) + chr(10) + url)}',
            f'LOCATION:{_ics_escape(_event_location(simposio, virtual))}',
            f'URL:{url}',
            'END:VEVENT',
        ]
    lines.append('END:VCALENDAR')
    return '\r\n'.join(lines) + '\r\n'


def google_calendar_links(simposio, virtual=False):
    """One «add to Google Calendar» link per day: [{'label', 'url'}]."""
    fmt = '%Y%m%dT%H%M%SZ'
    utc = datetime.timezone.utc
    site = settings.SITE_URL.rstrip('/')
    details = (
        'Participación virtual: el enlace de conexión llegará por correo antes del evento.'
        if virtual else 'Lleva tu entrada con el código QR.'
    )
    links = []
    for number, (start, end) in enumerate(simposio.sessions, start=1):
        query = urlencode({
            'action': 'TEMPLATE',
            'text': f'{simposio.title} (día {number})',
            'dates': f'{start.astimezone(utc).strftime(fmt)}/{end.astimezone(utc).strftime(fmt)}',
            'details': f'{details}\n\n{site}{simposio_landing_path()}',
            'location': _event_location(simposio, virtual),
            'ctz': 'America/Bogota',
        })
        label = date_format(timezone.localtime(start), 'l j \\d\\e F')
        links.append({'label': label[:1].upper() + label[1:].lower(), 'url': f'https://calendar.google.com/calendar/render?{query}'})
    return links


def simposio_landing_path():
    from django.urls import reverse
    return reverse('simposio:landing')


def send_confirmation_email(inscripcion, from_waitlist=False):
    """Registration confirmation.

    In person: the QR ticket (linked image + attachment). Virtual: the
    registration is confirmed and the connection details will follow.
    Both carry the dates as a calendar invitation (.ics) and Google Calendar links.
    On the waiting list: their place in line, no ticket. `from_waitlist`
    words the in-person ticket as "a seat freed up for you".
    """
    if inscripcion.is_waitlisted:
        return send_waitlist_email(inscripcion)
    simposio = inscripcion.simposio
    site = settings.SITE_URL.rstrip('/')
    virtual = inscripcion.is_virtual
    context = {
        'inscripcion': inscripcion,
        'simposio': simposio,
        'ticket_url': inscripcion.get_ticket_url(),
        'qr_url': f"{site}{inscripcion.get_ticket_path()}qr.png",
        'calendar_links': google_calendar_links(simposio, virtual=virtual),
        'from_waitlist': from_waitlist,
    }
    template = 'simposio/emails/confirmacion_virtual.html' if virtual else 'simposio/emails/confirmacion.html'
    html = render_to_string(template, context)
    if virtual:
        subject = f'Inscripción virtual confirmada: {simposio.title}'
    elif from_waitlist:
        subject = f'Se liberó un cupo: tu entrada al {simposio.title}'
    else:
        subject = f'Registro presencial confirmado: {simposio.title}'
    email = EmailMultiAlternatives(
        subject=subject,
        body=strip_tags(html),
        from_email=_from_email(),
        to=[inscripcion.email],
    )
    email.attach_alternative(html, 'text/html')
    if not virtual:
        # Attached too, so the ticket works offline and when images are blocked.
        email.attach('entrada-qr.png', ticket_qr_png(inscripcion), 'image/png')
    if simposio.sessions:
        email.attach('simposio.ics', calendar_ics(simposio, virtual=virtual), 'text/calendar')
    email.send(fail_silently=False)

    inscripcion.confirmation_sent_at = timezone.now()
    inscripcion.save(update_fields=['confirmation_sent_at', 'updated_at'])


def send_waitlist_email(inscripcion):
    """The room is full: the person is on the in-person waiting list (no ticket yet)."""
    simposio = inscripcion.simposio
    html = render_to_string('simposio/emails/lista_espera.html', {
        'inscripcion': inscripcion,
        'simposio': simposio,
        'position': inscripcion.waitlist_position,
        'ticket_url': inscripcion.get_ticket_url(),
    })
    email = EmailMultiAlternatives(
        subject=f'Estás en la lista de espera: {simposio.title}',
        body=strip_tags(html),
        from_email=_from_email(),
        to=[inscripcion.email],
    )
    email.attach_alternative(html, 'text/html')
    email.send(fail_silently=False)

    inscripcion.confirmation_sent_at = timezone.now()
    inscripcion.save(update_fields=['confirmation_sent_at', 'updated_at'])


def give_seats(simposio, inscripciones):
    """Move people off the waiting list while there are free seats.

    Locks the edition so two admins can't hand out the same seat. Returns
    the registrations that got a seat (in line order); the ticket e-mail is
    sent by the caller, outside the transaction.
    """
    with transaction.atomic():
        locked = Simposio.objects.select_for_update().get(pk=simposio.pk)
        seats = locked.seats_left
        promoted = []
        for inscripcion in inscripciones:
            if seats <= 0:
                break
            if not inscripcion.is_waitlisted:
                continue
            inscripcion.status = Inscripcion.Status.CONFIRMED
            inscripcion.save(update_fields=['status', 'updated_at'])
            promoted.append(inscripcion)
            seats -= 1
    return promoted


def send_certificate_emails(simposio, limit=25):
    """Send the "your certificate is ready" e-mail to the next `limit` attendees.

    Sent in small batches because the SMTP provider throttles bursts and a
    single request must finish well inside the gunicorn timeout.
    Returns (sent, failed, remaining).
    """
    pending = [
        i for i in simposio.inscripciones.filter(
            status=Inscripcion.Status.CONFIRMED, certificate_sent_at__isnull=True,
        ).prefetch_related('asistencias').order_by('pk')
        if i.can_get_certificate
    ]
    batch, sent, failed = pending[:limit], 0, 0

    if batch:
        connection = get_connection()
        try:
            connection.open()
            for inscripcion in batch:
                context = {
                    'inscripcion': inscripcion,
                    'simposio': simposio,
                    'certificate_url': inscripcion.get_certificate_url(),
                }
                html = render_to_string('simposio/emails/certificado.html', context)
                email = EmailMultiAlternatives(
                    subject=f'Tu certificado de asistencia · {simposio.title}',
                    body=strip_tags(html),
                    from_email=_from_email(),
                    to=[inscripcion.email],
                    connection=connection,
                )
                email.attach_alternative(html, 'text/html')
                try:
                    email.send(fail_silently=False)
                except Exception:
                    failed += 1
                    logger.exception(
                        'No se pudo enviar el certificado de la inscripción %s', inscripcion.pk,
                    )
                    continue
                inscripcion.certificate_sent_at = timezone.now()
                inscripcion.save(update_fields=['certificate_sent_at', 'updated_at'])
                sent += 1
        finally:
            connection.close()

    return sent, failed, len(pending) - sent


# ---------------------------------------------------------------- Certificate

def format_event_dates(simposio):
    """«12 de marzo de 2027» / «12 y 13 de marzo de 2027» / «del 12 al 14 de marzo de 2027»."""
    start, end = simposio.starts_on, simposio.last_day
    if not start:
        return ''
    # Lower-cased: some locale catalogs capitalise month names.
    def long(day):
        return date_format(day, r'j \d\e F \d\e Y').lower()

    if not simposio.is_multiday:
        return long(start)
    if (start.year, start.month) == (end.year, end.month):
        if (end - start).days == 1:
            return f'{start.day} y {long(end)}'
        return f'del {start.day} al {long(end)}'
    if start.year == end.year:
        start_text = date_format(start, r'j \d\e F').lower()
        return f'del {start_text} al {long(end)}'
    return f'del {long(start)} al {long(end)}'


def generate_certificate_pdf(inscripcion):
    """Landscape A4 attendance certificate. Returns a BytesIO."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph
    from xml.sax.saxutils import escape

    navy = colors.HexColor('#1B2A41')
    gold = colors.HexColor('#f4c343')
    grey = colors.HexColor('#5b6676')

    simposio = inscripcion.simposio
    width, height = landscape(A4)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(width, height))
    c.setTitle(f'Certificado de asistencia - {inscripcion.full_name}')
    c.setAuthor('Asociación Nuclear Colombiana')

    # Frame
    c.setStrokeColor(navy)
    c.setLineWidth(2.2)
    c.rect(12 * mm, 12 * mm, width - 24 * mm, height - 24 * mm)
    c.setStrokeColor(gold)
    c.setLineWidth(1)
    c.rect(15 * mm, 15 * mm, width - 30 * mm, height - 30 * mm)

    # Logo
    logo_path = settings.BASE_DIR / 'static' / 'images' / 'asnc_logo_full.png'
    top = height - 26 * mm
    if logo_path.exists():
        try:
            logo = ImageReader(str(logo_path))
            lw, lh = logo.getSize()
            draw_h = 24 * mm
            draw_w = draw_h * lw / lh
            c.drawImage(
                logo, (width - draw_w) / 2, top - draw_h, draw_w, draw_h, mask='auto',
            )
        except Exception:
            logger.exception('No se pudo dibujar el logo en el certificado')
    y = top - 24 * mm - 13 * mm

    c.setFillColor(navy)
    c.setFont('Helvetica-Bold', 25)
    c.drawCentredString(width / 2, y, 'CERTIFICADO DE ASISTENCIA')
    c.setFillColor(gold)
    c.rect(width / 2 - 22 * mm, y - 5 * mm, 44 * mm, 1.2 * mm, stroke=0, fill=1)

    y -= 17 * mm
    c.setFillColor(grey)
    c.setFont('Helvetica', 12.5)
    c.drawCentredString(width / 2, y, 'La Asociación Nuclear Colombiana certifica que')

    # Name (shrinks to fit)
    y -= 15 * mm
    name = inscripcion.full_name.upper()
    size = 27
    while size > 14 and c.stringWidth(name, 'Helvetica-Bold', size) > width - 70 * mm:
        size -= 1
    c.setFillColor(navy)
    c.setFont('Helvetica-Bold', size)
    c.drawCentredString(width / 2, y, name)

    y -= 8 * mm
    c.setFillColor(grey)
    c.setFont('Helvetica', 11.5)
    if inscripcion.document_number:
        c.drawCentredString(
            width / 2, y,
            f'{inscripcion.get_document_type_display()} n.º {inscripcion.document_number}',
        )

    # Body
    parts = [f'asistió al <b>{escape(simposio.title)}</b>']
    dates = format_event_dates(simposio)
    if dates:
        if dates.startswith('del '):
            prefix = ''
        elif simposio.is_multiday:
            prefix = 'los días '
        else:
            prefix = 'el '
        parts.append(f'realizado {prefix}{dates}')
    place = ', '.join(p for p in (simposio.venue, simposio.city) if p)
    if place:
        parts.append(f'en {escape(place)}')
    text = ', '.join(parts)
    if simposio.certificate_hours:
        text += f', con una intensidad de {simposio.certificate_hours} horas'
    text += '.'
    style = ParagraphStyle(
        'body', fontName='Helvetica', fontSize=13.5, leading=20,
        alignment=TA_CENTER, textColor=navy,
    )
    paragraph = Paragraph(text, style)
    max_w = width - 80 * mm
    _, ph = paragraph.wrap(max_w, 60 * mm)
    y -= 9 * mm
    paragraph.drawOn(c, (width - max_w) / 2, y - ph)

    # Signature
    sig_y = 40 * mm
    if simposio.signer_name:
        c.setStrokeColor(navy)
        c.setLineWidth(0.8)
        c.line(width / 2 - 38 * mm, sig_y, width / 2 + 38 * mm, sig_y)
        c.setFillColor(navy)
        c.setFont('Helvetica-Bold', 11.5)
        c.drawCentredString(width / 2, sig_y - 5.5 * mm, simposio.signer_name)
        if simposio.signer_role:
            c.setFillColor(grey)
            c.setFont('Helvetica', 10)
            c.drawCentredString(width / 2, sig_y - 10.5 * mm, simposio.signer_role)

    # Verification QR + code
    verify_url = inscripcion.get_certificate_verify_url()
    qr = generate_qr_code(verify_url, size=300)
    qr_size = 24 * mm
    qr_x, qr_y = width - 20 * mm - qr_size, 20 * mm
    c.drawImage(ImageReader(qr), qr_x, qr_y, qr_size, qr_size)
    c.setFillColor(grey)
    c.setFont('Helvetica', 7.5)
    c.drawRightString(qr_x - 3 * mm, qr_y + 9 * mm, 'Verifica este certificado escaneando el código')
    c.drawRightString(qr_x - 3 * mm, qr_y + 5 * mm, f'Código: {inscripcion.code}')

    c.setFont('Helvetica', 7.5)
    c.drawString(20 * mm, 20 * mm, 'www.asncol.com · info@asncol.com')

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer
