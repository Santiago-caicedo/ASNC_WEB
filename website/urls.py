from django.urls import path
from .views import HomeView, AboutView, EventsView, PowerPointTemplateView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('quienes-somos/', AboutView.as_view(), name='about'),
    path('eventos/', EventsView.as_view(), name='events'),
    path('recursos/plantilla-presentacion/', PowerPointTemplateView.as_view(), name='powerpoint_template'),
]