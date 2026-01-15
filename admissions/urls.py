from django.urls import path
from .views import ApplicationCreateView, ApplicationSuccessView

urlpatterns = [
    path('solicitud/', ApplicationCreateView.as_view(), name='application_create'),
    path('gracias/', ApplicationSuccessView.as_view(), name='application_success'),
]