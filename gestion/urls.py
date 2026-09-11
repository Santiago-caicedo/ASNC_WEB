from django.urls import path

from . import views

app_name = 'gestion'

urlpatterns = [
    path('', views.GestionHomeView.as_view(), name='home'),

    # Comités
    path('comites/', views.ComiteListView.as_view(), name='comite_list'),
    path('comites/nuevo/', views.ComiteCreateView.as_view(), name='comite_create'),
    path('comites/<int:pk>/', views.ComiteDetailView.as_view(), name='comite_detail'),
    path('comites/<int:pk>/editar/', views.ComiteUpdateView.as_view(), name='comite_update'),
    path('comites/<int:pk>/eliminar/', views.ComiteDeleteView.as_view(), name='comite_delete'),
    path('comites/<int:pk>/miembros/agregar/', views.add_member, name='comite_add_member'),
    path('comites/miembros/<int:pk>/rol/', views.update_member, name='comite_update_member'),
    path('comites/miembros/<int:pk>/quitar/', views.remove_member, name='comite_remove_member'),

    # Personas
    path('personas/', views.PersonaListView.as_view(), name='persona_list'),
    path('personas/nueva/', views.PersonaCreateView.as_view(), name='persona_create'),
    path('personas/importar-asociados/', views.import_users, name='persona_import'),
    path('personas/<int:pk>/', views.PersonaDetailView.as_view(), name='persona_detail'),
    path('personas/<int:pk>/editar/', views.PersonaUpdateView.as_view(), name='persona_update'),
    path('personas/<int:pk>/eliminar/', views.PersonaDeleteView.as_view(), name='persona_delete'),

    # Proyectos
    path('proyectos/', views.ProyectoListView.as_view(), name='proyecto_list'),
    path('proyectos/nuevo/', views.ProyectoCreateView.as_view(), name='proyecto_create'),
    path('proyectos/<int:pk>/', views.ProyectoDetailView.as_view(), name='proyecto_detail'),
    path('proyectos/<int:pk>/editar/', views.ProyectoUpdateView.as_view(), name='proyecto_update'),
    path('proyectos/<int:pk>/eliminar/', views.ProyectoDeleteView.as_view(), name='proyecto_delete'),
    path('proyectos/<int:pk>/estado/<str:estado>/', views.change_project_status, name='proyecto_estado'),

    # Tareas
    path('tareas/', views.TareaListView.as_view(), name='tarea_list'),
    path('tareas/tablero/', views.TareaBoardView.as_view(), name='tarea_board'),
    path('tareas/nueva/', views.TareaCreateView.as_view(), name='tarea_create'),
    path('tareas/<int:pk>/', views.TareaDetailView.as_view(), name='tarea_detail'),
    path('tareas/<int:pk>/editar/', views.TareaUpdateView.as_view(), name='tarea_update'),
    path('tareas/<int:pk>/eliminar/', views.TareaDeleteView.as_view(), name='tarea_delete'),
    path('tareas/<int:pk>/estado/<str:estado>/', views.change_task_status, name='tarea_estado'),

    # Notas de seguimiento
    path('notas/agregar/<str:kind>/<int:pk>/', views.add_note, name='nota_add'),
    path('notas/<int:pk>/eliminar/', views.delete_note, name='nota_delete'),
]
