from django.contrib import admin

from .models import (
    Convocatoria, ConvocatoriaField, ConvocatoriaSubmission, ConvocatoriaSubmissionFile,
)


class ConvocatoriaFieldInline(admin.TabularInline):
    model = ConvocatoriaField
    extra = 1
    fields = ('order', 'label', 'field_type', 'required', 'options')


@admin.register(Convocatoria)
class ConvocatoriaAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'opens_at', 'closes_at', 'submissions_count', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ConvocatoriaFieldInline]
    readonly_fields = ('uuid', 'created_at', 'updated_at')


class ConvocatoriaSubmissionFileInline(admin.TabularInline):
    model = ConvocatoriaSubmissionFile
    extra = 0
    readonly_fields = ('field_label', 'file', 'uploaded_at')
    can_delete = False


@admin.register(ConvocatoriaSubmission)
class ConvocatoriaSubmissionAdmin(admin.ModelAdmin):
    list_display = ('convocatoria', 'summary', 'submitted_at', 'ip_address')
    list_filter = ('convocatoria', 'submitted_at')
    readonly_fields = ('uuid', 'convocatoria', 'data', 'submitted_at', 'ip_address')
    inlines = [ConvocatoriaSubmissionFileInline]
    date_hierarchy = 'submitted_at'

    def has_add_permission(self, request):
        return False
