from django.urls import path
from .views import (
    # Public views
    CardVerificationView,
    PhotoUploadView,
    PhotoUploadSuccessView,
    # Associate views
    MyCardView,
    MyCardDownloadView,
    # Dashboard views
    CardListView,
    CardDetailView,
    GenerateCardView,
    CardSuspendView,
    CardRenewView,
    CardStatsView,
    reactivate_card,
    resend_photo_request,
)

app_name = 'carnets'

urlpatterns = [
    # Public URLs (no login required)
    path('verificar/<uuid:uuid>/', CardVerificationView.as_view(), name='verificar'),
    path('carnes/subir-foto/<uuid:token>/', PhotoUploadView.as_view(), name='subir_foto'),
    path('carnes/subir-foto/<uuid:token>/exito/', PhotoUploadSuccessView.as_view(), name='subir_foto_exito'),

    # Associate URLs (login required)
    path('mi-carne/', MyCardView.as_view(), name='mi_carne'),
    path('mi-carne/descargar/', MyCardDownloadView.as_view(), name='mi_carne_descargar'),

    # Dashboard URLs (admin - login required)
    path('portal/carnes/', CardListView.as_view(), name='card_list'),
    path('portal/carnes/estadisticas/', CardStatsView.as_view(), name='card_stats'),
    path('portal/carnes/<int:pk>/', CardDetailView.as_view(), name='card_detail'),
    path('portal/carnes/<int:pk>/suspender/', CardSuspendView.as_view(), name='card_suspend'),
    path('portal/carnes/<int:pk>/reactivar/', reactivate_card, name='card_reactivate'),
    path('portal/carnes/<int:pk>/renovar/', CardRenewView.as_view(), name='card_renew'),
    path('portal/carnes/<int:pk>/reenviar-solicitud/', resend_photo_request, name='resend_photo_request'),

    # Generate card from application (in dashboard context)
    path('portal/solicitudes/<int:pk>/generar-carne/', GenerateCardView.as_view(), name='generate_card'),
]
