from django.urls import path
from .views import (
    HomeView, AboutView, AdvisoryCommitteeView, EventsView, PowerPointTemplateView,
    PrivacyPolicyView, NewsListView, NewsCategoryDetailView,
    NewsDetailView, ContactView, enso_data,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    # Datos del Observatorio ENSO que consume el tablero de la portada.
    path('datos/enso.json', enso_data, name='enso_data'),
    path('quienes-somos/', AboutView.as_view(), name='about'),
    path('comite-asesor/', AdvisoryCommitteeView.as_view(), name='advisory_committee'),
    path('eventos/', EventsView.as_view(), name='events'),
    path('contacto/', ContactView.as_view(), name='contact'),
    path('noticias/', NewsListView.as_view(), name='public_news_list'),
    path('noticias/categoria/<slug:slug>/', NewsCategoryDetailView.as_view(), name='public_news_category'),
    path('noticias/<slug:slug>/', NewsDetailView.as_view(), name='public_news_detail'),
    path('recursos/plantilla-presentacion/', PowerPointTemplateView.as_view(), name='powerpoint_template'),
    path('politica-de-privacidad/', PrivacyPolicyView.as_view(), name='privacy_policy'),
]