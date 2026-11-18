from django import template

from simposio.utils import format_event_dates

register = template.Library()


@register.simple_tag
def event_dates(simposio):
    """Human-readable dates of the edition (see utils.format_event_dates)."""
    return format_event_dates(simposio)
