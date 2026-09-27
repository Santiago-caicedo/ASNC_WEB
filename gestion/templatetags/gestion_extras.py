from django import template

register = template.Library()


@register.filter
def iniciales(user):
    """Dos letras para el avatar de un usuario registrado."""
    if not user:
        return '—'
    partes = [(user.first_name or '')[:1], (user.last_name or '')[:1]]
    letras = ''.join(p for p in partes if p).upper()
    return letras or (user.email or '?')[:1].upper()


@register.filter
def nombre(user):
    if not user:
        return ''
    return user.get_full_name() or user.email
