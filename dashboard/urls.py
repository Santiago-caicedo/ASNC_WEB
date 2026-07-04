from django.urls import path
from django.contrib.auth.views import (
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from .views import (
    CustomLoginView, DashboardHomeView,
    FeaturedMemberListView, FeaturedMemberCreateView,
    FeaturedMemberUpdateView, FeaturedMemberDeleteView,
    NewsListView, NewsCreateView, NewsUpdateView, NewsDeleteView,
    NewsCategoryListView, NewsCategoryCreateView, NewsCategoryUpdateView,
    NewsCategoryDeleteView,
    news_image_upload,
    EmailComposeView, EmailHistoryView, EmailDetailView,
    DirectoryListView, DirectoryDetailView,
    UserListView, UserDetailView, UserRoleUpdateView,
)
from admissions.views import (
    ApplicationDetailView, ApplicationListView, change_application_status,
    resend_password_email, update_application_admin,
    export_applications_csv, export_applications_excel,
)

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', DashboardHomeView.as_view(), name='dashboard_home'),

    # Password set (for new users from approved applications)
    path(
        'configurar-contrasena/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(
            template_name='dashboard/password_set.html',
            success_url='/portal/contrasena-configurada/'
        ),
        name='password_set'
    ),
    path(
        'contrasena-configurada/',
        PasswordResetCompleteView.as_view(
            template_name='dashboard/password_set_done.html'
        ),
        name='password_set_complete'
    ),

    # Ruta para ver las solicitudes dentro del dashboard
    path('solicitudes/', ApplicationListView.as_view(), name='application_list'),
    path('solicitudes/exportar/csv/', export_applications_csv, name='export_applications_csv'),
    path('solicitudes/exportar/excel/', export_applications_excel, name='export_applications_excel'),
    path('solicitudes/<int:pk>/', ApplicationDetailView.as_view(), name='application_detail'),
    path('solicitudes/<int:pk>/cambiar-estado/<str:status>/', change_application_status, name='change_status'),
    path('solicitudes/<int:pk>/actualizar-gestion/', update_application_admin, name='update_application_admin'),
    path('solicitudes/<int:pk>/reenviar-correo-contrasena/', resend_password_email, name='resend_password_email'),

    # CRUD Asociados Destacados
    path('asociados-destacados/', FeaturedMemberListView.as_view(), name='featured_member_list'),
    path('asociados-destacados/nuevo/', FeaturedMemberCreateView.as_view(), name='featured_member_create'),
    path('asociados-destacados/<int:pk>/editar/', FeaturedMemberUpdateView.as_view(), name='featured_member_update'),
    path('asociados-destacados/<int:pk>/eliminar/', FeaturedMemberDeleteView.as_view(), name='featured_member_delete'),

    # CRUD Noticias
    path('noticias/', NewsListView.as_view(), name='news_list'),
    path('noticias/nueva/', NewsCreateView.as_view(), name='news_create'),
    path('noticias/<int:pk>/editar/', NewsUpdateView.as_view(), name='news_update'),
    path('noticias/<int:pk>/eliminar/', NewsDeleteView.as_view(), name='news_delete'),
    path('noticias/subir-imagen/', news_image_upload, name='news_image_upload'),

    # Categorías de noticias
    path('noticias/categorias/', NewsCategoryListView.as_view(), name='news_category_list'),
    path('noticias/categorias/nueva/', NewsCategoryCreateView.as_view(), name='news_category_create'),
    path('noticias/categorias/<int:pk>/editar/', NewsCategoryUpdateView.as_view(), name='news_category_update'),
    path('noticias/categorias/<int:pk>/eliminar/', NewsCategoryDeleteView.as_view(), name='news_category_delete'),

    # Módulo de Correos
    path('correos/', EmailHistoryView.as_view(), name='email_history'),
    path('correos/redactar/', EmailComposeView.as_view(), name='email_compose'),
    path('correos/<int:pk>/', EmailDetailView.as_view(), name='email_detail'),

    # Directorio Oficial de Asociados
    path('directorio/', DirectoryListView.as_view(), name='directory_list'),
    path('directorio/<int:pk>/', DirectoryDetailView.as_view(), name='directory_detail'),

    # Gestión de Usuarios
    path('usuarios/', UserListView.as_view(), name='user_list'),
    path('usuarios/<int:pk>/', UserDetailView.as_view(), name='user_detail'),
    path('usuarios/<int:pk>/rol/', UserRoleUpdateView.as_view(), name='user_role_update'),
]
