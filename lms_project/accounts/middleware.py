# accounts/middleware.py

from datetime import date
from .utils import send_deadline_reminders_for_user

class DeadlineReminderMiddleware:
    """
    При первом запросе пользователя за день проверяет дедлайны
    и создаёт напоминания.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Выполняем только для аутентифицированного пользователя
        if request.user.is_authenticated:
            # Стащим дату последней проверки из сессии
            last = request.session.get('last_deadline_reminder')
            today = date.today().isoformat()
            if last != today:
                # Рассылаем все дедлайн-уведомления
                send_deadline_reminders_for_user(request.user)
                # Ставим метку, чтобы не повторять в этот день
                request.session['last_deadline_reminder'] = today

        response = self.get_response(request)
        return response
