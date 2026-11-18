import datetime
import io
import json
import logging
import re

from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.cache import cache
from django.core.paginator import Paginator
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import FormView, TemplateView, UpdateView

from admissions.views import AdminRequiredMixin, admin_required
from config.exports import sanitize_spreadsheet_value
from dashboard.views import StaffRequiredMixin

from .forms import InscripcionForm, SimposioForm
from .models import Asistencia, Inscripcion, Simposio
from .utils import (
    calendar_ics, check_in, extract_ticket_uuid, format_event_dates, generate_certificate_pdf,
    google_calendar_links, send_certificate_emails, send_confirmation_email,
    ticket_qr_data_uri, ticket_qr_png,
)

logger = logging.getLogger(__name__)

# Registrations per IP per hour. Generous on purpose: a whole university or
# company often shares one public IP.
RATE_LIMIT_PER_HOUR = 20
MIN_FILL_SECONDS = 3


def staff_required(view_func):
    return user_passes_test(
        lambda u: u.is_authenticated and (u.is_staff or u.is_superuser),
        login_url='/acceso/',
    )(view_func)


def _is_admin(user):
    return user.is_authenticated and (user.is_superuser or (user.is_staff and user.is_admin))


def _client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '') or None


def get_public_simposio(request):
    """Current edition, or 404. Unpublished editions are a preview for admins."""
    simposio = Simposio.objects.actual()
    if simposio is None:
        raise Http404('No hay simposio')
    if not simposio.is_published and not _is_admin(request.user):
        raise Http404('Simposio sin publicar')
    return simposio


# =====================================================================
# Public
# =====================================================================

class LandingView(TemplateView):
    template_name = 'simposio/landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        simposio = get_public_simposio(self.request)
        context.update({
            'simposio': simposio,
            'event_dates': format_event_dates(simposio),
            'countdown_iso': self._countdown_iso(simposio),
            'date_block': self._date_block(simposio),
            'maps_query': ', '.join(
                p for p in (simposio.venue, simposio.address, simposio.city) if p
            ),
        })
        return context

    @staticmethod
    def _date_block(simposio):
        """Parts of the cover date block: «3 y 4» / «diciembre» / «2026»."""
        start, end = simposio.starts_on, simposio.last_day
        if not start:
            return None
        days = str(start.day)
        if simposio.is_multiday and (start.year, start.month) == (end.year, end.month):
            joiner = ' y ' if (end - start).days == 1 else ' al '
            days = f'{start.day}{joiner}{end.day}'
        return {'days': days, 'month': date_format(start, 'F').lower(), 'year': start.year}

    @staticmethod
    def _countdown_iso(simposio):
        """Start of the first session (first time in the agenda, else 8:00), Bogotá time."""
        if not simposio.starts_on:
            return ''
        hour, minute = 8, 0
        for item in simposio.agenda_items:
            match = re.match(r'\s*(\d{1,2}):(\d{2})', item.get('time', ''))
            if match and int(match.group(1)) < 24 and int(match.group(2)) < 60:
                hour, minute = int(match.group(1)), int(match.group(2))
                break
        start = timezone.make_aware(
            datetime.datetime.combine(simposio.starts_on, datetime.time(hour, minute))
        )
        return start.isoformat()


class RegistroView(FormView):
    template_name = 'simposio/registro.html'
    form_class = InscripcionForm

    def dispatch(self, request, *args, **kwargs):
        self.simposio = get_public_simposio(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'simposio': self.simposio,
            'event_dates': format_event_dates(self.simposio),
            'form_token': TimestampSigner().sign('simposio'),
        })
        return context

    def post(self, request, *args, **kwargs):
        if not self.simposio.accepts_registrations:
            return redirect('simposio:registro')
        return super().post(request, *args, **kwargs)

    def _token_error(self, token):
        """Signed-timestamp check: rejects missing/forged tokens and instant submits."""
        if not token:
            return 'Error en el formulario. Por favor recarga la página.'
        signer = TimestampSigner()
        try:
            signer.unsign(token, max_age=86400)
        except SignatureExpired:
            return 'La sesión del formulario ha expirado. Por favor recarga la página.'
        except BadSignature:
            return 'Error en el formulario. Por favor recarga la página.'
        try:
            signer.unsign(token, max_age=MIN_FILL_SECONDS)
        except SignatureExpired:
            return None  # took longer than the minimum: a human
        return 'Por favor toma un momento para completar el formulario.'

    def form_valid(self, form):
        error = self._token_error(form.cleaned_data.get('form_token', ''))
        if error:
            form.add_error(None, error)
            return self.form_invalid(form)

        ip = _client_ip(self.request)
        rate_key = f'simposio_rate_{ip}'
        attempts = cache.get(rate_key, 0)
        if attempts >= RATE_LIMIT_PER_HOUR:
            form.add_error(None, 'Se han enviado demasiadas inscripciones desde esta red. Intenta más tarde.')
            return self.form_invalid(form)

        email = form.cleaned_data['email']
        duplicate = False
        try:
            with transaction.atomic():
                # Lock the edition row so two simultaneous sign-ups can't both
                # take the last seat.
                simposio = Simposio.objects.select_for_update().get(pk=self.simposio.pk)
                existing = simposio.inscripciones.filter(email=email).first()
                if existing:
                    inscripcion, duplicate = existing, True
                elif not simposio.accepts_registrations:
                    form.add_error(None, 'Las inscripciones están cerradas.')
                    return self.form_invalid(form)
                elif (form.cleaned_data['modality'] == Inscripcion.Modality.IN_PERSON
                      and simposio.is_full):
                    form.add_error(
                        'modality',
                        'Se agotaron los cupos presenciales. Puedes inscribirte en modalidad virtual.',
                    )
                    return self.form_invalid(form)
                else:
                    inscripcion = form.save(commit=False)
                    inscripcion.simposio = simposio
                    inscripcion.ip_address = ip
                    inscripcion.save()
        except IntegrityError:
            inscripcion = self.simposio.inscripciones.get(email=email)
            duplicate = True

        cache.set(rate_key, attempts + 1, 3600)

        if duplicate:
            # Someone typing an e-mail that is already registered only gets the
            # ticket re-sent to that address: never shown on screen.
            resend_key = f'simposio_resend_{inscripcion.pk}'
            if inscripcion.is_confirmed and not cache.get(resend_key):
                cache.set(resend_key, True, 600)
                self._send(inscripcion)
            self.request.session['simposio_ya_inscrito'] = True
            self.request.session.pop('simposio_ticket', None)
        else:
            self._send(inscripcion)
            self.request.session['simposio_ticket'] = str(inscripcion.uuid)
            self.request.session.pop('simposio_ya_inscrito', None)

        return redirect('simposio:gracias')

    @staticmethod
    def _send(inscripcion):
        try:
            send_confirmation_email(inscripcion)
        except Exception:
            # The registration stands; the ticket is on screen and can be re-sent.
            logger.exception(
                'Fallo al enviar la confirmación de la inscripción %s', inscripcion.pk,
            )


class GraciasView(TemplateView):
    template_name = 'simposio/gracias.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        simposio = get_public_simposio(self.request)
        inscripcion = None
        ticket = self.request.session.get('simposio_ticket')
        if ticket:
            inscripcion = Inscripcion.objects.filter(uuid=ticket, simposio=simposio).first()
        context.update({
            'simposio': simposio,
            'inscripcion': inscripcion,
            'ya_inscrito': self.request.session.get('simposio_ya_inscrito', False),
        })
        return context


class EntradaView(TemplateView):
    """The ticket: QR, event facts and, after the event, the certificate."""
    template_name = 'simposio/entrada.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inscripcion = get_object_or_404(
            Inscripcion.objects.select_related('simposio'), uuid=kwargs['uuid'],
        )
        context.update({
            'inscripcion': inscripcion,
            'simposio': inscripcion.simposio,
            'event_dates': format_event_dates(inscripcion.simposio),
            'qr_data_uri': (
                ticket_qr_data_uri(inscripcion)
                if inscripcion.is_confirmed and not inscripcion.is_virtual else None
            ),
            'asistencias': inscripcion.asistencias.order_by('day'),
            'calendar_links': google_calendar_links(inscripcion.simposio, virtual=inscripcion.is_virtual),
        })
        return context


def entrada_ics(request, uuid):
    """The symposium dates as a calendar file, worded for the registration's modality."""
    inscripcion = get_object_or_404(Inscripcion.objects.select_related('simposio'), uuid=uuid)
    response = HttpResponse(
        calendar_ics(inscripcion.simposio, virtual=inscripcion.is_virtual),
        content_type='text/calendar; charset=utf-8',
    )
    response['Content-Disposition'] = 'attachment; filename="simposio.ics"'
    return response


def entrada_qr(request, uuid):
    """QR as a PNG, so e-mail clients can load it as a normal image."""
    inscripcion = get_object_or_404(Inscripcion, uuid=uuid, status=Inscripcion.Status.CONFIRMED)
    response = HttpResponse(ticket_qr_png(inscripcion), content_type='image/png')
    response['Cache-Control'] = 'private, max-age=86400'
    return response


def certificado(request, uuid):
    inscripcion = get_object_or_404(Inscripcion.objects.select_related('simposio'), uuid=uuid)
    if not inscripcion.can_get_certificate:
        messages.info(request, 'Tu certificado todavía no está disponible.')
        return redirect(inscripcion.get_ticket_path())
    pdf = generate_certificate_pdf(inscripcion)
    response = HttpResponse(pdf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="certificado-simposio-{inscripcion.code}.pdf"'
    return response


class VerificarCertificadoView(TemplateView):
    """Public page behind the certificate's QR: is this certificate real?"""
    template_name = 'simposio/verificar_certificado.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inscripcion = get_object_or_404(
            Inscripcion.objects.select_related('simposio'), uuid=kwargs['uuid'],
        )
        document = inscripcion.document_number
        context.update({
            'inscripcion': inscripcion,
            'simposio': inscripcion.simposio,
            'event_dates': format_event_dates(inscripcion.simposio),
            'valid': inscripcion.can_get_certificate,
            # Enough to recognise the holder, not enough to copy the ID.
            'masked_document': '•' * max(len(document) - 3, 0) + document[-3:] if document else '',
        })
        return context


# =====================================================================
# Portal (/portal/simposio/)
# =====================================================================

def get_admin_simposio():
    simposio = Simposio.objects.actual()
    if simposio is None:
        simposio = Simposio.objects.create(title='Simposio Nuclear Colombiano')
    return simposio


def _back(request, fallback='simposio_admin:list'):
    target = request.POST.get('next') or ''
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}):
        return redirect(target)
    return redirect(fallback)


def _filtered_inscripciones(request, simposio):
    today = timezone.localdate()
    queryset = simposio.inscripciones.annotate(
        dias=Count('asistencias', distinct=True),
        hoy=Count('asistencias', filter=Q(asistencias__day=today), distinct=True),
    )
    search = request.GET.get('q', '').strip()
    if search:
        queryset = queryset.filter(
            Q(first_name__icontains=search) | Q(last_name__icontains=search)
            | Q(email__icontains=search) | Q(document_number__icontains=search)
            | Q(institution__icontains=search) | Q(uuid__istartswith=search)
        )
    estado = request.GET.get('estado', '')
    if estado == 'asistieron':
        queryset = queryset.filter(dias__gt=0)
    elif estado == 'sin_asistencia':
        queryset = queryset.filter(dias=0, status=Inscripcion.Status.CONFIRMED)
    elif estado == 'canceladas':
        queryset = queryset.filter(status=Inscripcion.Status.CANCELLED)
    tipo = request.GET.get('tipo', '')
    if tipo in Inscripcion.AttendeeType.values:
        queryset = queryset.filter(attendee_type=tipo)
    modalidad = request.GET.get('modalidad', '')
    if modalidad in Inscripcion.Modality.values:
        queryset = queryset.filter(modality=modalidad)
    return queryset.order_by('-created_at')


class InscripcionListView(AdminRequiredMixin, TemplateView):
    template_name = 'simposio/portal/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        simposio = get_admin_simposio()
        today = timezone.localdate()
        confirmed = simposio.inscripciones.filter(status=Inscripcion.Status.CONFIRMED)
        attended = confirmed.filter(asistencias__isnull=False).distinct().count()

        page = Paginator(_filtered_inscripciones(self.request, simposio), 25).get_page(
            self.request.GET.get('page')
        )
        params = self.request.GET.copy()
        params.pop('page', None)

        pending_certificates = 0
        if simposio.certificates_enabled:
            pending_certificates = sum(
                1 for i in confirmed.filter(certificate_sent_at__isnull=True)
                .prefetch_related('asistencias')
                if i.can_get_certificate
            )

        context.update({
            'simposio': simposio,
            'event_dates': format_event_dates(simposio),
            'page_obj': page,
            'querystring': params.urlencode(),
            'total_confirmed': confirmed.count(),
            'total_in_person': confirmed.filter(modality=Inscripcion.Modality.IN_PERSON).count(),
            'total_virtual': confirmed.filter(modality=Inscripcion.Modality.VIRTUAL).count(),
            'total_attended': attended,
            'attended_today': Asistencia.objects.filter(
                inscripcion__simposio=simposio, day=today,
            ).count(),
            'pending_certificates': pending_certificates,
            'tipos': Inscripcion.AttendeeType.choices,
            'q': self.request.GET.get('q', ''),
            'estado': self.request.GET.get('estado', ''),
            'tipo': self.request.GET.get('tipo', ''),
            'modalidad': self.request.GET.get('modalidad', ''),
            'modalidades': Inscripcion.Modality.choices,
        })
        return context


class SimposioConfigView(AdminRequiredMixin, UpdateView):
    form_class = SimposioForm
    template_name = 'simposio/portal/config.html'

    def get_object(self, queryset=None):
        return get_admin_simposio()

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Simposio actualizado.')
        return redirect('simposio_admin:config')


class EscanearView(StaffRequiredMixin, TemplateView):
    """Door screen: the phone camera reads the QR and marks attendance."""
    template_name = 'simposio/portal/escanear.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        simposio = get_admin_simposio()
        context.update({
            'simposio': simposio,
            'attended_today': Asistencia.objects.filter(
                inscripcion__simposio=simposio, day=timezone.localdate(),
            ).count(),
            'total_confirmed': simposio.confirmed_count,
        })
        return context


def _checkin_payload(inscripcion, ok, code, message, simposio):
    return {
        'ok': ok,
        'code': code,
        'message': message,
        'name': inscripcion.full_name,
        'detail': ' · '.join(
            p for p in (inscripcion.get_attendee_type_display(), inscripcion.institution) if p
        ),
        'attended_today': Asistencia.objects.filter(
            inscripcion__simposio=simposio, day=timezone.localdate(),
        ).count(),
    }


@staff_required
@require_POST
def checkin_api(request):
    """JSON endpoint used by the scanner. Body: {"code": "<what the QR says>"}."""
    try:
        payload = json.loads(request.body or b'{}')
    except ValueError:
        payload = {}
    ticket = extract_ticket_uuid(str(payload.get('code', '')))
    simposio = get_admin_simposio()
    inscripcion = None
    if ticket:
        inscripcion = Inscripcion.objects.filter(uuid=ticket, simposio=simposio).first()
    if inscripcion is None:
        return JsonResponse({
            'ok': False, 'code': 'unknown',
            'message': 'Este código no corresponde a una inscripción del simposio.',
        })
    ok, code, message, _ = check_in(inscripcion, request.user, Asistencia.Method.QR)
    return JsonResponse(_checkin_payload(inscripcion, ok, code, message, simposio))


class CheckinTicketView(StaffRequiredMixin, TemplateView):
    """Where the QR lands when read with the phone's own camera app.

    GET shows the ticket; attendance is only written on POST, so opening or
    pre-fetching the link never marks anyone as present.
    """
    template_name = 'simposio/portal/checkin_ticket.html'

    def get_inscripcion(self):
        return get_object_or_404(
            Inscripcion.objects.select_related('simposio'), uuid=self.kwargs['uuid'],
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        inscripcion = kwargs.get('inscripcion') or self.get_inscripcion()
        context.update({
            'inscripcion': inscripcion,
            'simposio': inscripcion.simposio,
            'asistencias': inscripcion.asistencias.order_by('day'),
            'today_done': inscripcion.asistencias.filter(day=timezone.localdate()).exists(),
            'result': kwargs.get('result'),
        })
        return context

    def post(self, request, *args, **kwargs):
        inscripcion = self.get_inscripcion()
        ok, code, message, _ = check_in(inscripcion, request.user, Asistencia.Method.QR)
        return self.render_to_response(self.get_context_data(
            inscripcion=inscripcion, result={'ok': ok, 'code': code, 'message': message},
        ))


@admin_required
@require_POST
def asistencia_manual(request, pk):
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    ok, code, message, _ = check_in(inscripcion, request.user, Asistencia.Method.MANUAL)
    notify = messages.success if code == 'ok' else messages.warning
    notify(request, f'{inscripcion.full_name}: {message}')
    return _back(request)


@admin_required
@require_POST
def asistencia_quitar(request, pk):
    """Undo today's check-in (a ticket scanned by mistake)."""
    inscripcion = get_object_or_404(Inscripcion, pk=pk)
    deleted, _ = inscripcion.asistencias.filter(day=timezone.localdate()).delete()
    if deleted:
        messages.success(request, f'Se quitó la asistencia de hoy de {inscripcion.full_name}.')
    return _back(request)


@admin_required
@require_POST
def inscripcion_estado(request, pk):
    """Cancel or restore a registration (frees or takes a seat)."""
    inscripcion = get_object_or_404(Inscripcion.objects.select_related('simposio'), pk=pk)
    if inscripcion.is_confirmed:
        inscripcion.status = Inscripcion.Status.CANCELLED
        messages.success(request, f'Inscripción de {inscripcion.full_name} cancelada.')
    else:
        inscripcion.status = Inscripcion.Status.CONFIRMED
        messages.success(request, f'Inscripción de {inscripcion.full_name} restablecida.')
    inscripcion.save(update_fields=['status', 'updated_at'])
    return _back(request)


@admin_required
@require_POST
def reenviar_confirmacion(request, pk):
    inscripcion = get_object_or_404(Inscripcion.objects.select_related('simposio'), pk=pk)
    if not inscripcion.is_confirmed:
        messages.warning(request, 'La inscripción está cancelada: no se envió el correo.')
        return _back(request)
    try:
        send_confirmation_email(inscripcion)
    except Exception:
        logger.exception('Fallo al reenviar la confirmación de la inscripción %s', pk)
        messages.error(request, f'No se pudo enviar el correo a {inscripcion.email}.')
    else:
        messages.success(request, f'Entrada reenviada a {inscripcion.email}.')
    return _back(request)


@admin_required
@require_POST
def enviar_certificados(request):
    simposio = get_admin_simposio()
    if not simposio.certificates_enabled:
        messages.warning(request, 'Primero habilita los certificados en la configuración.')
        return redirect('simposio_admin:list')
    sent, failed, remaining = send_certificate_emails(simposio)
    if sent:
        messages.success(request, f'Se enviaron {sent} certificados.')
    if failed:
        messages.error(request, f'{failed} correos fallaron; se reintentarán en el siguiente envío.')
    if remaining:
        messages.info(request, f'Quedan {remaining} por enviar: pulsa «Enviar certificados» de nuevo.')
    elif not sent and not failed:
        messages.info(request, 'No hay certificados pendientes por enviar.')
    return redirect('simposio_admin:list')


@admin_required
def exportar_excel(request):
    """All registrations of the edition (respecting the list filters) as .xlsx."""
    import xlsxwriter

    simposio = get_admin_simposio()
    rows = _filtered_inscripciones(request, simposio).prefetch_related('asistencias')

    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True, 'remove_timezone': True})
    sheet = workbook.add_worksheet('Inscritos')
    header = workbook.add_format({
        'bold': True, 'font_color': '#FFFFFF', 'bg_color': '#1B2A41',
        'border': 1, 'valign': 'vcenter',
    })
    date_fmt = workbook.add_format({'num_format': 'dd/mm/yyyy hh:mm'})
    yes = workbook.add_format({'bg_color': '#DCFCE7', 'font_color': '#166534'})
    off = workbook.add_format({'bg_color': '#FEE2E2', 'font_color': '#991B1B'})

    columns = [
        ('Código', 12), ('Nombres', 22), ('Apellidos', 22), ('Modalidad', 12),
        ('Correo', 32), ('Teléfono', 18), ('Asiste como', 22),
        ('Institución', 30), ('Profesión o cargo', 26), ('Ciudad', 18),
        ('Estado', 14), ('Inscrito el', 18), ('Días asistidos', 14),
        ('Fechas de asistencia', 26), ('Certificado enviado', 18),
    ]
    for col, (title, width) in enumerate(columns):
        sheet.write(0, col, title, header)
        sheet.set_column(col, col, width)

    clean = sanitize_spreadsheet_value
    for row, i in enumerate(rows, start=1):
        days = sorted(a.day for a in i.asistencias.all())
        values = [
            i.code, clean(i.first_name), clean(i.last_name), i.get_modality_display(),
            clean(i.email), clean(i.phone),
            i.get_attendee_type_display(), clean(i.institution), clean(i.position),
            clean(i.city),
        ]
        for col, value in enumerate(values):
            sheet.write(row, col, value)
        sheet.write(row, 10, i.get_status_display(), yes if i.is_confirmed else off)
        sheet.write_datetime(row, 11, timezone.localtime(i.created_at).replace(tzinfo=None), date_fmt)
        sheet.write(row, 12, len(days), yes if days else None)
        sheet.write(row, 13, ', '.join(date_format(d, 'd/m/Y') for d in days))
        sheet.write(row, 14, 'Sí' if i.certificate_sent_at else 'No')

    sheet.freeze_panes(1, 0)
    sheet.autofilter(0, 0, max(len(rows), 1), len(columns) - 1)
    workbook.close()

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    filename = f'inscritos_simposio_{timezone.localdate():%Y%m%d}.xlsx'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
