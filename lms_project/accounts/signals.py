import logging
from datetime import timedelta, date

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Notification
from submissions.models import Submission
from practice.models import PracticeAssignment
from homework.models import Homework
from exams.models import StudentExam, ExamSubmission
from submissions.utils import get_student_mentor

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Submission)
def notify_on_grade(sender, instance, **kwargs):
    """
    Уведомляет студента при авто- или ручной проверке его решения.
    """
    if instance.status not in ('auto-graded', 'graded'):
        return

    user = instance.student
    ex_id = instance.exercise_id
    # тестовые задания
    if instance.exercise.exercise_type == 'test':
        if instance.status == 'auto-graded':
            text = f"Ваш ответ на задачу №{ex_id} автоматически проверен."
        else:
            text = f"Ваш ответ на задачу №{ex_id} проверен ментором."
    # открытые задания
    else:
        if instance.status == 'auto-graded':
            text = f"Ваше решение по задаче №{ex_id} автоматически оценено."
        else:
            text = f"Ваше решение по задаче №{ex_id} проверено ментором."

    Notification.objects.create(user=user, text=text)
    logger.debug(f"[notify_on_grade] {user}: {text}")


@receiver(post_save, sender=PracticeAssignment)
def notify_new_practice(sender, instance, created, **kwargs):
    """
    Уведомляет студента о новой отработке.
    """
    if not created:
        return
    user = instance.student
    text = f"Новая отработка по теме «{instance.theme.name}», дедлайн {instance.deadline:%d.%m.%Y}."
    Notification.objects.create(user=user, text=text)
    logger.debug(f"[notify_new_practice] {user}: {text}")


@receiver(post_save, sender=Submission)
def notify_mentor_on_submission(sender, instance, created, **kwargs):
    """
    Уведомляет ментора, когда студент отправил решение (status='pending').
    Работает и для домашки, и для отработки.
    """
    # Показываем только новые сабмиты на проверку
    if not created or instance.status != 'pending':
        return

    mentor = instance.grader
    # Если для этой задачи ментор не назначен — ищем по группе
    if mentor is None:
        mentor = get_student_mentor(instance.student.id)
    if not mentor:
        return
    ex = instance.exercise
    # Определяем контекст: домашка или отработка?
    # Для красоты в тексте можно упомянуть тему/раздел
    theme = ex.theme.name if hasattr(ex, 'theme') and ex.theme else ''

    text = (
        f"Новое решение на проверку от {instance.student.get_full_name()}: "
        f"задание №{ex.pk} ({'тема: ' + theme if theme else 'часть 2'})."
    )
    Notification.objects.create(user=mentor, text=text)
    logger.debug(f"[notify_mentor_on_submission] {mentor}: {text}")


@receiver(post_save, sender=StudentExam)
def notify_new_exam(sender, instance, created, **kwargs):
    """
    Уведомляет ментора о новом пробном экзамене или о готовности к проверке.
    """
    student = instance.student
    mentor = get_student_mentor(student.id)
    if not mentor:
        return

    if created:
        text = (
            f"Новый пробный экзамен от {student.get_full_name()}: "
            f"«{instance.variant.name}», до {instance.deadline:%d.%m.%Y %H:%M}."
        )
    else:
        # уведомление при переходе к проверке (статус pending_review)
        if instance.completed_at and instance.status == 'pending_review':
            text = (
                f"Пробник «{instance.variant.name}» от {student.get_full_name()} "
                "готов к проверке."
            )
        else:
            return

    Notification.objects.create(user=mentor, text=text)
    logger.debug(f"[notify_new_exam] {mentor}: {text}")


@receiver(post_save, sender=ExamSubmission)
def notify_exam_submission(sender, instance, **kwargs):
    """
    Уведомляет студента о проверенном задании второй части пробника.
    """
    if instance.status != 'graded':
        return
    user = instance.exam.student
    ex_num = instance.exercise_id
    text = (
        f"Часть 2 пробного экзамена №{instance.exam_id}, задача {ex_num} проверена ментором."
    )
    Notification.objects.create(user=user, text=text)
    logger.debug(f"[notify_exam_submission] {user}: {text}")
