import csv

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import (
    CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView, View,
)

from dashboard.views import AdminRequiredMixin

from .forms import ConvocatoriaFieldForm, ConvocatoriaForm, SubmissionForm
from config.exports import sanitize_spreadsheet_value
from .models import (
    Convocatoria, ConvocatoriaField, ConvocatoriaSubmission, ConvocatoriaSubmissionFile,
)


# ============================================================================
# Helpers
# ============================================================================


def _client_ip(request):
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ============================================================================
# Public views
# ============================================================================


class PublicConvocatoriaListView(ListView):
    """Public listing of active convocatorias."""
    template_name = 'convocatorias/public/list.html'
    context_object_name = 'convocatorias'

    def get_queryset(self):
        now = timezone.now()
        qs = Convocatoria.objects.filter(is_active=True)
        # Show those already open or not yet closed
        return qs.order_by('-created_at')


class PublicConvocatoriaDetailView(View):
    """Public detail page that also hosts the dynamic form."""
    template_name = 'convocatorias/public/detail.html'

    def get_convocatoria(self, slug):
        return get_object_or_404(
            Convocatoria.objects.prefetch_related('fields'),
            slug=slug,
            is_active=True,
        )

    def get(self, request, slug):
        convocatoria = self.get_convocatoria(slug)
        form = SubmissionForm(convocatoria=convocatoria) if convocatoria.is_open else None
        return render(request, self.template_name, {
            'convocatoria': convocatoria,
            'form': form,
        })

    def post(self, request, slug):
        convocatoria = self.get_convocatoria(slug)
        if not convocatoria.is_open:
            messages.error(request, 'Esta convocatoria no está recibiendo inscripciones.')
            return redirect('convocatorias:detail', slug=slug)

        form = SubmissionForm(request.POST, request.FILES, convocatoria=convocatoria)
        if not form.is_valid():
            return render(request, self.template_name, {
                'convocatoria': convocatoria,
                'form': form,
            })

        data = {}
        files_to_save = []
        for cfield, bound in form.iter_rendered_fields():
            if cfield is None:
                continue
            value = form.cleaned_data.get(cfield.input_name)
            if cfield.field_type == ConvocatoriaField.FieldType.FILE:
                if value:
                    files_to_save.append((cfield.label, value))
                    data[cfield.label] = value.name
                else:
                    data[cfield.label] = ''
            elif cfield.field_type == ConvocatoriaField.FieldType.DATE:
                data[cfield.label] = value.isoformat() if value else ''
            elif cfield.field_type == ConvocatoriaField.FieldType.CHECKBOX:
                data[cfield.label] = bool(value)
            else:
                data[cfield.label] = value if value is not None else ''

        submission = ConvocatoriaSubmission.objects.create(
            convocatoria=convocatoria,
            data=data,
            ip_address=_client_ip(request),
        )
        for label, fileobj in files_to_save:
            ConvocatoriaSubmissionFile.objects.create(
                submission=submission,
                field_label=label,
                file=fileobj,
            )

        return redirect('convocatorias:success', slug=slug)


class PublicConvocatoriaSuccessView(TemplateView):
    template_name = 'convocatorias/public/success.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['convocatoria'] = get_object_or_404(
            Convocatoria, slug=kwargs['slug'], is_active=True
        )
        return ctx


# ============================================================================
# Admin views
# ============================================================================


class ConvocatoriaListView(AdminRequiredMixin, ListView):
    model = Convocatoria
    template_name = 'convocatorias/admin/list.html'
    context_object_name = 'convocatorias'
    paginate_by = 20


class ConvocatoriaCreateView(AdminRequiredMixin, CreateView):
    model = Convocatoria
    form_class = ConvocatoriaForm
    template_name = 'convocatorias/admin/form.html'

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Convocatoria creada. Ahora agrega los campos del formulario.')
        return response

    def get_success_url(self):
        return reverse('convocatorias_admin:fields', kwargs={'pk': self.object.pk})


class ConvocatoriaUpdateView(AdminRequiredMixin, UpdateView):
    model = Convocatoria
    form_class = ConvocatoriaForm
    template_name = 'convocatorias/admin/form.html'

    def get_success_url(self):
        messages.success(self.request, 'Convocatoria actualizada.')
        return reverse('convocatorias_admin:detail', kwargs={'pk': self.object.pk})


class ConvocatoriaDetailView(AdminRequiredMixin, DetailView):
    model = Convocatoria
    template_name = 'convocatorias/admin/detail.html'
    context_object_name = 'convocatoria'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['fields'] = self.object.fields.all()
        ctx['recent_submissions'] = self.object.submissions.all()[:10]
        public_url = self.request.build_absolute_uri(
            reverse('convocatorias:detail', kwargs={'slug': self.object.slug})
        )
        ctx['public_url'] = public_url
        return ctx


class ConvocatoriaDeleteView(AdminRequiredMixin, DeleteView):
    model = Convocatoria
    template_name = 'convocatorias/admin/confirm_delete.html'
    success_url = reverse_lazy('convocatorias_admin:list')

    def form_valid(self, form):
        messages.success(self.request, 'Convocatoria eliminada.')
        return super().form_valid(form)


# ---- Field management ----

class ConvocatoriaFieldsView(AdminRequiredMixin, TemplateView):
    """List and add fields for a convocatoria."""
    template_name = 'convocatorias/admin/fields.html'

    def get(self, request, pk):
        convocatoria = get_object_or_404(Convocatoria, pk=pk)
        return render(request, self.template_name, {
            'convocatoria': convocatoria,
            'fields': convocatoria.fields.all(),
            'form': ConvocatoriaFieldForm(initial={'order': (convocatoria.fields.count() + 1) * 10}),
        })

    def post(self, request, pk):
        convocatoria = get_object_or_404(Convocatoria, pk=pk)
        form = ConvocatoriaFieldForm(request.POST)
        if form.is_valid():
            cf = form.save(commit=False)
            cf.convocatoria = convocatoria
            cf.save()
            messages.success(request, f'Campo "{cf.label}" agregado.')
            return redirect('convocatorias_admin:fields', pk=pk)
        return render(request, self.template_name, {
            'convocatoria': convocatoria,
            'fields': convocatoria.fields.all(),
            'form': form,
        })


class ConvocatoriaFieldUpdateView(AdminRequiredMixin, UpdateView):
    model = ConvocatoriaField
    form_class = ConvocatoriaFieldForm
    template_name = 'convocatorias/admin/field_form.html'
    pk_url_kwarg = 'field_pk'

    def get_queryset(self):
        return ConvocatoriaField.objects.filter(convocatoria_id=self.kwargs['pk'])

    def get_success_url(self):
        messages.success(self.request, 'Campo actualizado.')
        return reverse('convocatorias_admin:fields', kwargs={'pk': self.kwargs['pk']})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['convocatoria'] = self.object.convocatoria
        return ctx


class ConvocatoriaFieldDeleteView(AdminRequiredMixin, View):
    def post(self, request, pk, field_pk):
        field = get_object_or_404(ConvocatoriaField, pk=field_pk, convocatoria_id=pk)
        field.delete()
        messages.success(request, 'Campo eliminado.')
        return redirect('convocatorias_admin:fields', pk=pk)


# ---- Submissions ----

class ConvocatoriaSubmissionListView(AdminRequiredMixin, ListView):
    template_name = 'convocatorias/admin/submissions.html'
    context_object_name = 'submissions'
    paginate_by = 50

    def get_queryset(self):
        return ConvocatoriaSubmission.objects.filter(
            convocatoria_id=self.kwargs['pk']
        ).order_by('-submitted_at')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['convocatoria'] = get_object_or_404(Convocatoria, pk=self.kwargs['pk'])
        return ctx


class ConvocatoriaSubmissionDetailView(AdminRequiredMixin, DetailView):
    model = ConvocatoriaSubmission
    template_name = 'convocatorias/admin/submission_detail.html'
    context_object_name = 'submission'
    pk_url_kwarg = 'submission_pk'

    def get_queryset(self):
        return ConvocatoriaSubmission.objects.filter(convocatoria_id=self.kwargs['pk'])


class ConvocatoriaSubmissionExportView(AdminRequiredMixin, View):
    """Export all submissions of a convocatoria as CSV."""

    def get(self, request, pk):
        convocatoria = get_object_or_404(Convocatoria, pk=pk)
        submissions = convocatoria.submissions.order_by('submitted_at')

        # Collect all labels from all submissions, preserving order from fields
        labels = [f.label for f in convocatoria.fields.all()]
        for sub in submissions:
            for key in sub.data.keys():
                if key not in labels:
                    labels.append(key)

        response = HttpResponse(content_type='text/csv; charset=utf-8')
        filename = f'inscripciones_{convocatoria.slug}.csv'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.write('\ufeff')  # BOM for Excel UTF-8
        writer = csv.writer(response)
        writer.writerow(['Fecha', 'IP'] + [sanitize_spreadsheet_value(l) for l in labels])
        for sub in submissions:
            row = [sub.submitted_at.strftime('%Y-%m-%d %H:%M'), sub.ip_address or '']
            for label in labels:
                row.append(sub.data.get(label, ''))
            # Los valores los escribe el público en el formulario dinámico
            writer.writerow([sanitize_spreadsheet_value(v) for v in row])
        return response
