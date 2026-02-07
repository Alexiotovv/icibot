# verificaciones/templatetags/verificaciones_tags.py
from django import template
from verificaciones.db_utils import get_nombre_establecimiento

register = template.Library()

@register.filter
def get_nombre_ipress(cod_ipress):
    return get_nombre_establecimiento(cod_ipress)