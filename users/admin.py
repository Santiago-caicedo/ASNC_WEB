from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model."""

    list_display = (
        'email',
        'full_name',
        'is_staff_badge',
        'has_card_badge',
        'is_active',
        'date_joined',
    )

    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')

    search_fields = ('email', 'first_name', 'last_name', 'username')

    ordering = ('-date_joined',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información Personal', {'fields': ('first_name', 'last_name', 'username')}),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',),
        }),
        ('Fechas', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',),
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    def full_name(self, obj):
        return obj.get_full_name() or '-'
    full_name.short_description = 'Nombre Completo'
    full_name.admin_order_field = 'first_name'

    def is_staff_badge(self, obj):
        if obj.is_superuser:
            return format_html(
                '<span style="background-color: #dc3545; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">Superadmin</span>'
            )
        elif obj.is_staff:
            return format_html(
                '<span style="background-color: #17a2b8; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">Staff</span>'
            )
        return format_html(
            '<span style="background-color: #6c757d; color: white; padding: 3px 8px; border-radius: 10px; font-size: 11px;">Usuario</span>'
        )
    is_staff_badge.short_description = 'Rol'

    def has_card_badge(self, obj):
        if hasattr(obj, 'member_card'):
            card = obj.member_card
            if card.status == 'ACTIVE':
                return format_html(
                    '<span style="color: green;" title="{}">&#10004; {}</span>',
                    card.card_number,
                    card.card_number
                )
            else:
                return format_html(
                    '<span style="color: orange;" title="{}">{}</span>',
                    card.get_status_display(),
                    card.card_number
                )
        return format_html('<span style="color: #999;">Sin carné</span>')
    has_card_badge.short_description = 'Carné'
