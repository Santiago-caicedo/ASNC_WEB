from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    MemberLoginView,
    MemberDashboardView,
    MemberCardView,
    MemberCardDownloadView,
    MemberProfileView,
    MemberProfileEditView,
    MemberPasswordChangeView,
    MemberPasswordChangeDoneView,
)

app_name = 'members'

urlpatterns = [
    # Auth
    path('acceso/', MemberLoginView.as_view(), name='login'),
    path('salir/', LogoutView.as_view(next_page='/acceso/'), name='logout'),

    # Member Portal
    path('mi-portal/', MemberDashboardView.as_view(), name='dashboard'),
    path('mi-portal/carnet/', MemberCardView.as_view(), name='card'),
    path('mi-portal/carnet/descargar/', MemberCardDownloadView.as_view(), name='card_download'),
    path('mi-portal/perfil/', MemberProfileView.as_view(), name='profile'),
    path('mi-portal/perfil/editar/', MemberProfileEditView.as_view(), name='profile_edit'),

    # Password Change
    path('mi-portal/cambiar-contrasena/', MemberPasswordChangeView.as_view(), name='password_change'),
    path('mi-portal/contrasena-actualizada/', MemberPasswordChangeDoneView.as_view(), name='password_change_done'),
]
