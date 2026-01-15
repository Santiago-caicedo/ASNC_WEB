from django.contrib import admin
from django.utils.html import format_html
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .models import MembershipApplication

@admin.register(MembershipApplication)
class MembershipApplicationAdmin(admin.ModelAdmin):
    # 1. QUÉ COLUMNAS VER EN LA LISTA
    list_display = (
        'full_name', 
        'email', 
        'profession', 
        'status_colored', # Usamos una función para colorear el estado
        'cv_link',        # Link directo al PDF
        'created_at'
    )
    
    # 2. FILTROS LATERALES
    list_filter = ('status', 'created_at', 'profession')
    
    # 3. BARRA DE BÚSQUEDA
    search_fields = ('first_name', 'last_name', 'email', 'uuid')
    
    # 4. CAMPOS DE SOLO LECTURA (Para que el admin no altere la solicitud original)
    readonly_fields = ('uuid', 'created_at', 'updated_at')

    # 5. ACCIONES PERSONALIZADAS (Botones de "Aprobar" / "Rechazar")
    actions = ['approve_application', 'reject_application']

    # --- Funciones de visualización ---

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Nombre Completo'

    def cv_link(self, obj):
        if obj.cv_file:
            return format_html('<a href="{}" target="_blank" class="button">Ver PDF</a>', obj.cv_file.url)
        return "-"
    cv_link.short_description = 'Hoja de Vida'

    def status_colored(self, obj):
        # Colores según estado: Bootstrap colors
        colors = {
            'PENDING': 'orange',
            'REVIEW': 'blue',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'COMPLETED': 'black',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>', 
            color, 
            obj.get_status_display()
        )
    status_colored.short_description = 'Estado'

    # --- Lógica de Negocio (Actions) ---

    @admin.action(description='✅ APROBAR seleccionados y enviar notificación')
    def approve_application(self, request, queryset):
        # Filtramos solo los que no están aprobados ya
        updated_count = 0
        for application in queryset:
            if application.status != 'APPROVED':
                application.status = 'APPROVED'
                application.save()
                
                # Enviar Email de Aprobación
                send_mail(
                    subject='¡Solicitud Aprobada! - Asociación Nuclear Colombiana',
                    message=f"""
                    Estimado(a) {application.first_name},
                    
                    Nos complace informarle que su perfil ha sido aprobado por el Comité de Admisiones.
                    
                    Su código de acceso para formalizar la vinculación es: {application.uuid}
                    
                    Próximamente recibirá instrucciones para el pago de la membresía.
                    
                    Atentamente,
                    Junta Directiva ASNC
                    """,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[application.email],
                    fail_silently=True, # Para que no rompa si falla el correo en dev
                )
                updated_count += 1
        
        self.message_user(
            request, 
            f'{updated_count} solicitudes fueron aprobadas y notificadas exitosamente.',
            messages.SUCCESS
        )

    @admin.action(description='❌ RECHAZAR seleccionados')
    def reject_application(self, request, queryset):
        updated_count = queryset.update(status='REJECTED')
        
        # Opcional: Aquí también podrías poner lógica de email de rechazo
        
        self.message_user(
            request, 
            f'{updated_count} solicitudes fueron marcadas como rechazadas.',
            messages.WARNING
        )