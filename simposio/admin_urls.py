from django.urls import path

from . import views

app_name = 'simposio_admin'

urlpatterns = [
    path('', views.InscripcionListView.as_view(), name='list'),
    path('configuracion/', views.SimposioConfigView.as_view(), name='config'),
    path('exportar/excel/', views.exportar_excel, name='export_excel'),
    path('certificados/enviar/', views.enviar_certificados, name='enviar_certificados'),

    # Door check-in (any staff user)
    path('escanear/', views.EscanearView.as_view(), name='escanear'),
    path('checkin/', views.checkin_api, name='checkin_api'),
    path('checkin/<uuid:uuid>/', views.CheckinTicketView.as_view(), name='checkin_ticket'),

    path('inscripciones/<int:pk>/asistencia/', views.asistencia_manual, name='asistencia_manual'),
    path('inscripciones/<int:pk>/asistencia/quitar/', views.asistencia_quitar, name='asistencia_quitar'),
    path('inscripciones/<int:pk>/estado/', views.inscripcion_estado, name='inscripcion_estado'),
    path('inscripciones/<int:pk>/reenviar/', views.reenviar_confirmacion, name='reenviar'),

    # Waiting list
    path('inscripciones/<int:pk>/dar-cupo/', views.dar_cupo, name='dar_cupo'),
    path('lista-de-espera/dar-cupos/', views.dar_cupos_siguientes, name='dar_cupos_siguientes'),
]
