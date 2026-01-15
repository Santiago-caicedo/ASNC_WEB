from django.urls import path
from .views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    # Aquí luego agregaremos: path('nosotros/', ...), path('eventos/', ...)
]