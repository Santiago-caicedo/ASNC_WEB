from django import template

register = template.Library()

ESTADO_TAREA = {
    'PENDIENTE': 'bg-secondary-subtle text-secondary',
    'EN_PROGRESO': 'bg-primary-subtle text-primary',
    'EN_REVISION': 'bg-warning-subtle text-warning-emphasis',
    'COMPLETADA': 'bg-success-subtle text-success',
    'CANCELADA': 'bg-dark-subtle text-muted',
}

ESTADO_PROYECTO = {
    'IDEA': 'bg-light text-dark border',
    'PLANEACION': 'bg-info-subtle text-info-emphasis',
    'EN_CURSO': 'bg-primary-subtle text-primary',
    'PAUSADO': 'bg-warning-subtle text-warning-emphasis',
    'COMPLETADO': 'bg-success-subtle text-success',
    'CANCELADO': 'bg-dark-subtle text-muted',
}

PRIORIDAD = {
    'BAJA': 'bg-light text-muted border',
    'MEDIA': 'bg-info-subtle text-info-emphasis',
    'ALTA': 'bg-warning-subtle text-warning-emphasis',
    'URGENTE': 'bg-danger-subtle text-danger',
}

ROL = {
    'COORDINADOR': 'bg-warning text-dark',
    'SECRETARIO': 'bg-primary-subtle text-primary',
    'MIEMBRO': 'bg-light text-dark border',
    'COLABORADOR': 'bg-secondary-subtle text-secondary',
}

TIPO_PERSONA = {
    'ASOCIADO': 'bg-primary-subtle text-primary',
    'ALIADO': 'bg-info-subtle text-info-emphasis',
    'VOLUNTARIO': 'bg-success-subtle text-success',
    'INSTITUCION': 'bg-warning-subtle text-warning-emphasis',
    'PROVEEDOR': 'bg-secondary-subtle text-secondary',
    'OTRO': 'bg-light text-muted border',
}


@register.filter
def estado_tarea_class(value):
    return ESTADO_TAREA.get(value, 'bg-light text-dark')


@register.filter
def estado_proyecto_class(value):
    return ESTADO_PROYECTO.get(value, 'bg-light text-dark')


@register.filter
def prioridad_class(value):
    return PRIORIDAD.get(value, 'bg-light text-dark')


@register.filter
def rol_class(value):
    return ROL.get(value, 'bg-light text-dark')


@register.filter
def tipo_persona_class(value):
    return TIPO_PERSONA.get(value, 'bg-light text-dark')


@register.filter
def hex_alpha(value, alpha='18'):
    """Append an alpha channel to a #rrggbb color (for soft backgrounds)."""
    if isinstance(value, str) and len(value) == 7 and value.startswith('#'):
        return f'{value}{alpha}'
    return value
