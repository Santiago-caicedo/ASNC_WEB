from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect
from django.contrib.staticfiles.storage import staticfiles_storage

from website.sitemaps import StaticViewSitemap


def favicon_redirect(request):
    """Redirect to favicon using Django's static file storage (works with S3)."""
    favicon_url = staticfiles_storage.url('images/icon_asnc.png')
    return HttpResponseRedirect(favicon_url)

sitemaps = {
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),

    # SEO: Sitemap, robots.txt y favicon
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', TemplateView.as_view(template_name='robots.txt', content_type='text/plain'), name='robots'),
    path('favicon.ico', favicon_redirect, name='favicon'),

    # App Website (La raíz del sitio)
    path('', include('website.urls')),
    path('', include('admissions.urls')),
    path('portal/', include('dashboard.urls')),

    # Carnets (Digital Member Cards)
    path('', include('carnets.urls')),

    # Members Portal (for regular associates)
    path('', include('members.urls')),
]

# Configuración para servir archivos media en modo DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
