from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import FeaturedMember


@admin.register(FeaturedMember)
class FeaturedMemberAdmin(admin.ModelAdmin):
    """Admin configuration for FeaturedMember model."""

    list_display = (
        'photo_thumbnail',
        'full_name',
        'association_position',
        'profession',
        'is_active_badge',
        'display_order',
    )

    list_filter = ('is_active', 'created_at')

    search_fields = ('full_name', 'profession', 'association_position')

    list_editable = ('display_order',)

    ordering = ('display_order', 'full_name')

    fieldsets = (
        ('Información Personal', {
            'fields': ('full_name', 'photo', 'linkedin_url')
        }),
        ('Información en la Asociación', {
            'fields': ('association_position', 'profession', 'professional_trajectory')
        }),
        ('Visualización', {
            'fields': ('is_active', 'display_order')
        }),
    )

    def photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 50%; object-fit: cover;" />',
                obj.photo.url
            )
        return mark_safe('<span style="color: #999;">Sin foto</span>')
    photo_thumbnail.short_description = 'Foto'

    def is_active_badge(self, obj):
        if obj.is_active:
            return mark_safe(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">Activo</span>'
            )
        return mark_safe(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">Inactivo</span>'
        )
    is_active_badge.short_description = 'Estado'
