# content/templatetags/content_extras.py

from django import template
from ..models import VideoProgress

register = template.Library()


@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Возвращает dictionary[key] или 0, если нет такого ключа.
    Использование: {{ mydict|get_item:mykey }}
    """
    try:
        return dictionary.get(key, 0)
    except Exception:
        return 0


@register.filter
def get_user_progress(video, user):
    try:
        return VideoProgress.objects.get(video=video, student=user)
    except VideoProgress.DoesNotExist:
        return None
