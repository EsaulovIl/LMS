# accounts/utils.py

from datetime import timedelta
from django.utils import timezone
from homework.models import Homework
from practice.models import PracticeAssignment
from exams.models import StudentExam
from .models import Notification


def send_deadline_reminders_for_user(user):
    """
    Однократно за день/в день дедлайна присылает напоминания:
    - за день до дедлайна (deadline == tomorrow)
    - в день дедлайна (deadline == today)
    """
    today = timezone.localdate()
    tomorrow = today + timedelta(days=1)

    # 1) Домашки
    hw_qs = Homework.objects.filter(
        deadline__in=(today, tomorrow),
        schedule__plan__student=user
    )
    for hw in hw_qs:
        if hw.deadline == tomorrow:
            date_str = tomorrow.strftime("%d.%m.%Y")
            prefix = "Завтра"
        else:
            date_str = today.strftime("%d.%m.%Y")
            prefix = "Сегодня"
        text = (
            f"{prefix} дедлайн домашней работы по теме "
            f"«{hw.schedule.theme.name}»: {date_str}."
        )
        # не дублируем
        if not Notification.objects.filter(user=user, text=text).exists():
            Notification.objects.create(user=user, text=text)

    # 2) Отработки
    pa_qs = PracticeAssignment.objects.filter(
        deadline__in=(today, tomorrow),
        student=user
    )
    for pa in pa_qs:
        if pa.deadline == tomorrow:
            date_str = tomorrow.strftime("%d.%m.%Y")
            prefix = "Завтра"
        else:
            date_str = today.strftime("%d.%m.%Y")
            prefix = "Сегодня"
        text = (
            f"{prefix} дедлайн отработки по теме "
            f"«{pa.theme.name}»: {date_str}."
        )
        if not Notification.objects.filter(user=user, text=text).exists():
            Notification.objects.create(user=user, text=text)

    # 3) Пробники
    se_qs = StudentExam.objects.filter(
        student=user,
        completed_at__isnull=True,
        deadline__date__in=(today, tomorrow)
    )
    for se in se_qs:
        dl_date = se.deadline.date()
        if dl_date == tomorrow:
            date_str = tomorrow.strftime("%d.%m.%Y")
            prefix = "Завтра"
        else:
            date_str = today.strftime("%d.%m.%Y")
            prefix = "Сегодня"
        text = (
            f"{prefix} дедлайн пробного экзамена «{se.variant.name}»: {date_str}."
        )
        if not Notification.objects.filter(user=user, text=text).exists():
            Notification.objects.create(user=user, text=text)
