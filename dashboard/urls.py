from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView, DashboardHomeView
# Importaremos la lista de solicitudes en el siguiente paso, pero prepara la ruta
from admissions.views import ApplicationDetailView, ApplicationListView, change_application_status 

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', DashboardHomeView.as_view(), name='dashboard_home'),
    
    # Ruta para ver las solicitudes dentro del dashboard
    path('solicitudes/', ApplicationListView.as_view(), name='application_list'),

    path('solicitudes/<int:pk>/', ApplicationDetailView.as_view(), name='application_detail'),
    path('solicitudes/<int:pk>/cambiar-estado/<str:status>/', change_application_status, name='change_status'),
]