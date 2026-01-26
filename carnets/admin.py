from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import messages
from .models import MemberCard, CardVerification


@admin.register(MemberCard)
class MemberCardAdmin(admin.ModelAdmin):
    """Admin configuration for MemberCard model."""

    list_display = (
        'card_number',
        'user_name',
        'category_badge',
        'status_colored',
        'expiry_date',
        'photo_thumbnail',
        'created_at',
    )

    list_filter = ('status', 'category', 'issue_date', 'expiry_date')

    search_fields = (
        'card_number',
        'user__first_name',
        'user__last_name',
        'user__email',
        'uuid',
    )

    readonly_fields = (
        'uuid',
        'card_number',
        'photo_token',
        'photo_token_used',
        'created_at',
        'updated_at',
    )

    raw_id_fields = ('user', 'application', 'issued_by')

    fieldsets = (
        ('Identificación', {
            'fields': ('uuid', 'card_number', 'user', 'application')
        }),
        ('Datos del Carné', {
            'fields': ('photo', 'category', 'status')
        }),
        ('Vigencia', {
            'fields': ('issue_date', 'expiry_date')
        }),
        ('Administración', {
            'fields': ('issued_by', 'suspension_reason')
        }),
        ('Token de Foto', {
            'fields': ('photo_token', 'photo_token_used'),
            'classes': ('collapse',),
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['activate_cards', 'suspend_cards', 'expire_cards']

    # --- Display functions ---

    def user_name(self, obj):
        return obj.user.get_full_name()
    user_name.short_description = 'Asociado'
    user_name.admin_order_field = 'user__first_name'

    def photo_thumbnail(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />',
                obj.photo.url
            )
        return mark_safe('<span style="color: #999;">Sin foto</span>')
    photo_thumbnail.short_description = 'Foto'

    def category_badge(self, obj):
        colors = {
            'FOUNDER': '#f4c343',
            'ASSOCIATE': '#17a2b8',
        }
        color = colors.get(obj.category, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: #fff; padding: 3px 8px; border-radius: 10px; font-size: 11px;">{}</span>',
            color,
            obj.get_category_display()
        )
    category_badge.short_description = 'Categoría'

    def status_colored(self, obj):
        colors = {
            'PENDING_PHOTO': 'orange',
            'ACTIVE': 'green',
            'EXPIRED': 'gray',
            'SUSPENDED': 'red',
            'CANCELLED': 'black',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Estado'

    # --- Actions ---

    @admin.action(description='Activar carnés seleccionados')
    def activate_cards(self, request, queryset):
        count = 0
        for card in queryset:
            if card.photo and card.status != MemberCard.Status.ACTIVE:
                card.status = MemberCard.Status.ACTIVE
                card.save()
                count += 1
        self.message_user(
            request,
            f'{count} carnés fueron activados.',
            messages.SUCCESS
        )

    @admin.action(description='Suspender carnés seleccionados')
    def suspend_cards(self, request, queryset):
        count = queryset.update(status=MemberCard.Status.SUSPENDED)
        self.message_user(
            request,
            f'{count} carnés fueron suspendidos.',
            messages.WARNING
        )

    @admin.action(description='Marcar como expirados')
    def expire_cards(self, request, queryset):
        count = queryset.update(status=MemberCard.Status.EXPIRED)
        self.message_user(
            request,
            f'{count} carnés fueron marcados como expirados.',
            messages.WARNING
        )


@admin.register(CardVerification)
class CardVerificationAdmin(admin.ModelAdmin):
    """Admin configuration for CardVerification model."""

    list_display = ('card', 'verified_at', 'ip_address')
    list_filter = ('verified_at',)
    search_fields = ('card__card_number', 'ip_address')
    readonly_fields = ('card', 'verified_at', 'ip_address', 'user_agent')
    date_hierarchy = 'verified_at'

    def has_add_permission(self, request):
        # Verifications are created automatically, not manually
        return False

    def has_change_permission(self, request, obj=None):
        return False
