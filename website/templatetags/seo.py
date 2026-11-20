"""Template helpers for SEO and social-sharing tags."""
from django import template
from django.conf import settings

register = template.Library()


@register.filter
def absolute_url(url):
    """Return `url` as an absolute URL for og:image, JSON-LD and the like.

    In production `{% static %}` and `FileField.url` already return the full S3
    URL, so prefixing the site domain would give «https://www.asncol.comhttps://…»;
    locally they are relative paths. Absolute URLs pass through unchanged and
    relative ones get `SITE_URL` in front.
    """
    url = str(url or '')
    if not url or url.startswith(('http://', 'https://', '//')):
        return url
    return settings.SITE_URL.rstrip('/') + '/' + url.lstrip('/')
