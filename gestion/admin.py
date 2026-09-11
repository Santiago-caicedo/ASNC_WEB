from django.contrib import admin

from .models import Comite, MiembroComite, Nota, Persona, Proyecto, Tarea


class MiembroInline(admin.TabularInline):
    model = MiembroComite
    extra = 0
    autocomplete_fields = ['persona']


@admin.register(Comite)
class ComiteAdmin(admin.ModelAdmin):
    list_display = ['name', 'coordinator', 'is_active', 'order', 'active_members_count', 'open_tasks_count']
    list_editable = ['order', 'is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [MiembroInline]


@admin.register(Persona)
class PersonaAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'tipo', 'email', 'organization', 'user', 'is_active']
    list_filter = ['tipo', 'is_active']
    search_fields = ['first_name', 'last_name', 'email', 'organization']
    autocomplete_fields = ['user']


@admin.register(Proyecto)
class ProyectoAdmin(admin.ModelAdmin):
    list_display = ['title', 'comite', 'responsable', 'estado', 'prioridad', 'due_date', 'progress']
    list_filter = ['estado', 'prioridad', 'comite']
    search_fields = ['title', 'description']
    autocomplete_fields = ['responsable']


@admin.register(Tarea)
class TareaAdmin(admin.ModelAdmin):
    list_display = ['title', 'comite', 'proyecto', 'asignado_a', 'estado', 'prioridad', 'due_date']
    list_filter = ['estado', 'prioridad', 'comite']
    search_fields = ['title', 'description']
    autocomplete_fields = ['asignado_a', 'proyecto']
    date_hierarchy = 'created_at'


@admin.register(Nota)
class NotaAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'author', 'target', 'created_at']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
