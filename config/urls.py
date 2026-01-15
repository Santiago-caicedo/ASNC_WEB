from django.contrib import admin
from django.urls import include, path
from django.conf import settings # Importar settings
from django.conf.urls.static import static # Importar static

urlpatterns = [
    path('admin/', admin.site.urls),
    # App Website (La raíz del sitio)
    path('', include('website.urls')),
    path('', include('admissions.urls')),
    path('portal/', include('dashboard.urls')),
]

# Configuración para servir archivos media en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
