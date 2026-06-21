from django.urls import path
from .views import (
    HomeView, AboutView, EventsView, PowerPointTemplateView,
    PrivacyPolicyView, NewsListView, NewsDetailView, ContactView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('quienes-somos/', AboutView.as_view(), name='about'),
    path('eventos/', EventsView.as_view(), name='events'),
    path('contacto/', ContactView.as_view(), name='contact'),
    path('noticias/', NewsListView.as_view(), name='public_news_list'),
    path('noticias/<slug:slug>/', NewsDetailView.as_view(), name='public_news_detail'),
    path('recursos/plantilla-presentacion/', PowerPointTemplateView.as_view(), name='powerpoint_template'),
    path('politica-de-privacidad/', PrivacyPolicyView.as_view(), name='privacy_policy'),
]