from django.urls import path

from . import views

app_name = 'simposio'

urlpatterns = [
    path('', views.LandingView.as_view(), name='landing'),
    path('inscripcion/', views.RegistroView.as_view(), name='registro'),
    path('inscripcion/gracias/', views.GraciasView.as_view(), name='gracias'),
    path('entrada/<uuid:uuid>/', views.EntradaView.as_view(), name='entrada'),
    path('entrada/<uuid:uuid>/qr.png', views.entrada_qr, name='entrada_qr'),
    path('entrada/<uuid:uuid>/calendario.ics', views.entrada_ics, name='entrada_ics'),
    path('certificado/<uuid:uuid>/', views.certificado, name='certificado'),
    path(
        'certificado/<uuid:uuid>/verificar/',
        views.VerificarCertificadoView.as_view(), name='verificar_certificado',
    ),
]
