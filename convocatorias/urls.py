from django.urls import path

from . import views

app_name = 'convocatorias'

urlpatterns = [
    path('', views.PublicConvocatoriaListView.as_view(), name='list'),
    path('<slug:slug>/', views.PublicConvocatoriaDetailView.as_view(), name='detail'),
    path('<slug:slug>/gracias/', views.PublicConvocatoriaSuccessView.as_view(), name='success'),
]
