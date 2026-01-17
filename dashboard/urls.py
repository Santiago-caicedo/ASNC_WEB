from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import (
    CustomLoginView, DashboardHomeView,
    FeaturedMemberListView, FeaturedMemberCreateView,
    FeaturedMemberUpdateView, FeaturedMemberDeleteView
)
from admissions.views import ApplicationDetailView, ApplicationListView, change_application_status

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', DashboardHomeView.as_view(), name='dashboard_home'),

    # Ruta para ver las solicitudes dentro del dashboard
    path('solicitudes/', ApplicationListView.as_view(), name='application_list'),
    path('solicitudes/<int:pk>/', ApplicationDetailView.as_view(), name='application_detail'),
    path('solicitudes/<int:pk>/cambiar-estado/<str:status>/', change_application_status, name='change_status'),

    # CRUD Asociados Destacados
    path('asociados-destacados/', FeaturedMemberListView.as_view(), name='featured_member_list'),
    path('asociados-destacados/nuevo/', FeaturedMemberCreateView.as_view(), name='featured_member_create'),
    path('asociados-destacados/<int:pk>/editar/', FeaturedMemberUpdateView.as_view(), name='featured_member_update'),
    path('asociados-destacados/<int:pk>/eliminar/', FeaturedMemberDeleteView.as_view(), name='featured_member_delete'),
]