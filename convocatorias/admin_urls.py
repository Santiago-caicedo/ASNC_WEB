from django.urls import path

from . import views

app_name = 'convocatorias_admin'

urlpatterns = [
    path('', views.ConvocatoriaListView.as_view(), name='list'),
    path('nueva/', views.ConvocatoriaCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ConvocatoriaDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.ConvocatoriaUpdateView.as_view(), name='update'),
    path('<int:pk>/eliminar/', views.ConvocatoriaDeleteView.as_view(), name='delete'),

    path('<int:pk>/campos/', views.ConvocatoriaFieldsView.as_view(), name='fields'),
    path('<int:pk>/campos/<int:field_pk>/editar/',
         views.ConvocatoriaFieldUpdateView.as_view(), name='field_update'),
    path('<int:pk>/campos/<int:field_pk>/eliminar/',
         views.ConvocatoriaFieldDeleteView.as_view(), name='field_delete'),

    path('<int:pk>/inscripciones/',
         views.ConvocatoriaSubmissionListView.as_view(), name='submissions'),
    path('<int:pk>/inscripciones/exportar/',
         views.ConvocatoriaSubmissionExportView.as_view(), name='submission_export'),
    path('<int:pk>/inscripciones/<int:submission_pk>/',
         views.ConvocatoriaSubmissionDetailView.as_view(), name='submission_detail'),
]
