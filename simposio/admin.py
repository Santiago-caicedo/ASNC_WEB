from django.contrib import admin

from .models import Asistencia, Inscripcion, Simposio


@admin.register(Simposio)
class SimposioAdmin(admin.ModelAdmin):
    list_display = ('title', 'starts_on', 'ends_on', 'capacity', 'is_published', 'registration_open', 'is_active')
    list_filter = ('is_active', 'is_published')


class AsistenciaInline(admin.TabularInline):
    model = Asistencia
    extra = 0
    readonly_fields = ('checked_in_at',)


@admin.register(Inscripcion)
class InscripcionAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'modality', 'attendee_type', 'institution', 'status', 'created_at')
    list_filter = ('simposio', 'modality', 'status', 'attendee_type')
    search_fields = ('first_name', 'last_name', 'email', 'document_number', 'institution')
    readonly_fields = ('uuid', 'ip_address', 'created_at', 'updated_at')
    inlines = [AsistenciaInline]


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ('inscripcion', 'day', 'checked_in_at', 'method', 'checked_in_by')
    list_filter = ('day', 'method')
    search_fields = ('inscripcion__first_name', 'inscripcion__last_name', 'inscripcion__email')
