from django.urls import path

from . import views

app_name = 'gestion'

urlpatterns = [
    # Una sola pantalla: ?comite=<id> para elegir el comité, sin parámetro = vista general.
    path('', views.WorkspaceView.as_view(), name='workspace'),

    # Comités
    path('comites/nuevo/', views.comite_guardar, name='comite_create'),
    path('comites/<int:pk>/guardar/', views.comite_guardar, name='comite_update'),
    path('comites/<int:pk>/eliminar/', views.comite_eliminar, name='comite_delete'),

    # Integrantes (solo usuarios registrados)
    path('comites/<int:pk>/integrantes/agregar/', views.miembro_agregar, name='miembro_add'),
    path('integrantes/<int:pk>/rol/', views.miembro_rol, name='miembro_rol'),
    path('integrantes/<int:pk>/quitar/', views.miembro_quitar, name='miembro_remove'),

    # Proyectos
    path('proyectos/nuevo/', views.proyecto_guardar, name='proyecto_create'),
    path('proyectos/<int:pk>/guardar/', views.proyecto_guardar, name='proyecto_update'),
    path('proyectos/<int:pk>/estado/', views.proyecto_estado, name='proyecto_estado'),
    path('proyectos/<int:pk>/eliminar/', views.proyecto_eliminar, name='proyecto_delete'),

    # Tareas
    path('tareas/rapida/', views.tarea_rapida, name='tarea_quick'),
    path('tareas/nueva/', views.tarea_guardar, name='tarea_create'),
    path('tareas/<int:pk>/guardar/', views.tarea_guardar, name='tarea_update'),
    path('tareas/<int:pk>/estado/', views.tarea_estado, name='tarea_estado'),
    path('tareas/<int:pk>/eliminar/', views.tarea_eliminar, name='tarea_delete'),

    # Notas
    path('notas/<str:kind>/<int:pk>/agregar/', views.nota_agregar, name='nota_add'),
    path('notas/<int:pk>/eliminar/', views.nota_eliminar, name='nota_delete'),
]
