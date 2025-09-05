from django import template
register = template.Library()
@register.filter
def get_item(d, key):
    return d.get(key, 0)

@register.filter
def attr(obj, name):
    """Возвращает атрибут obj.name."""
    return getattr(obj, name, '')