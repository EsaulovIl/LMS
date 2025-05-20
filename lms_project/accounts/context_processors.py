# accounts/context_processors.py

from .models import Notification

def notifications(request):
    if request.user.is_authenticated:
        notes = request.user.notifications.order_by('-created_at')[:5]
        unread = request.user.notifications.filter(read_at__isnull=True).count()
    else:
        notes = []
        unread = 0
    return {
        'notifications': notes,
        'unread_count': unread,
    }
