from django.contrib import admin
from django.utils.html import format_html
from .models import SentEmail


@admin.register(SentEmail)
class SentEmailAdmin(admin.ModelAdmin):
    """Admin configuration for SentEmail model."""

    list_display = (
        'subject',
        'sent_by',
        'recipients_count',
        'success_badge',
        'sent_at',
    )

    list_filter = ('success', 'sent_at', 'sent_by')

    search_fields = ('subject', 'message', 'recipients')

    readonly_fields = (
        'subject',
        'message',
        'recipients',
        'recipients_count',
        'sent_by',
        'sent_at',
        'success',
        'error_message',
    )

    date_hierarchy = 'sent_at'

    ordering = ('-sent_at',)

    fieldsets = (
        ('Contenido', {
            'fields': ('subject', 'message')
        }),
        ('Destinatarios', {
            'fields': ('recipients', 'recipients_count')
        }),
        ('Envío', {
            'fields': ('sent_by', 'sent_at', 'success', 'error_message')
        }),
    )

    def success_badge(self, obj):
        if obj.success:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">Enviado</span>'
            )
        return format_html(
            '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">Error</span>'
        )
    success_badge.short_description = 'Estado'

    def has_add_permission(self, request):
        # Emails are sent through the dashboard, not created manually
        return False

    def has_change_permission(self, request, obj=None):
        # Email records are read-only
        return False

    def has_delete_permission(self, request, obj=None):
        # Only superusers can delete email history
        return request.user.is_superuser
