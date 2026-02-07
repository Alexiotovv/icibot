# verificaciones/templatetags/verificaciones_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Obtiene un valor de un diccionario usando una clave"""
    return dictionary.get(key, key)