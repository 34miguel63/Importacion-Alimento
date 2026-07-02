from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(obj, arg):
    """
    Filtro para acceder a campos de formulario o items de diccionario.
    Ejemplo: {{ form|get_item:"campo_nombre" }}
    """
    if obj is None:
        return None
    
    # Si es un diccionario
    if isinstance(obj, dict):
        return obj.get(arg)
    
    # Si es un formulario de Django (tiene campos)
    if hasattr(obj, 'fields'):
        try:
            return obj[arg]
        except (KeyError, TypeError):
            return None
    
    # Si es un QuerySet o lista
    try:
        return obj[arg]
    except (KeyError, TypeError, IndexError):
        return None