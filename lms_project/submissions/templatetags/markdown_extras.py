import markdown as _md
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='markdown')
def markdown(value):
    if not value:
        return ''
    html = _md.markdown(
        value,
        extensions=['fenced_code', 'tables', 'codehilite']
    )
    return mark_safe(html)
