from django.db import models
from django.conf import settings
from django.utils import timezone
from courses.models import Section
from content.models import Theme

from content.models import VideoLesson, VideoProgress
from django.apps import apps


class Plan(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Plan'


class PlanEntry(models.Model):
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='entries'
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='plan_entries'
    )
    order_idx = models.IntegerField(
        default=0,
        help_text="Порядок блока в плане (выдаётся алгоритмом)"
    )
    tasks_count = models.IntegerField(
        default=0,
        help_text="Сколько ЕГЭ-заданий брать из этого раздела"
    )

    class Meta:
        db_table = 'PlanEntry'
        unique_together = ('plan', 'section')
        ordering = ['order_idx']

    def __str__(self):
        return f"{self.plan.student}: {self.section} (#{self.order_idx})"


class ThemeSchedule(models.Model):
    """
    Каждая тема из плана получает конкретную дату выдачи
    и статус выполнения.
    """
    STATUS_PENDING = 'pending'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'В ожидании'),
        (STATUS_IN_PROGRESS, 'В процессе'),
        (STATUS_DONE, 'Выполнено'),
    ]
    plan = models.ForeignKey(
        Plan,
        on_delete=models.CASCADE,
        related_name='theme_schedules'
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE
    )
    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    scheduled_date = models.DateField(
        help_text="Дата, когда в календаре показываем эту тему"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Когда тема была отмечена выполненной"
    )

    class Meta:
        db_table = 'ThemeSchedule'
        unique_together = ('plan', 'section', 'theme')
        ordering = ['scheduled_date']

    def __str__(self):
        return (
            f"{self.plan.student} | {self.scheduled_date} | "
            f"{self.section} → {self.theme}"
        )

    def recalculate_status(self):
        """
        Пересчитывает и сохраняет self.status / self.completed_at
        на основе прогресса по видео и домашке.
        """
        student = self.plan.student

        # --- Прогресс по видео ---
        lessons = VideoLesson.objects.filter(theme=self.theme)
        prog_qs = VideoProgress.objects.filter(student=student, video__in=lessons)
        theory_started = any(vp.watched_percent > 0 for vp in prog_qs)
        theory_done = lessons.exists() and all(vp.viewed for vp in prog_qs)

        # --- Прогресс по домашке — динамический импорт Homework ---
        Homework = apps.get_model('homework', 'Homework')
        try:
            hw = Homework.objects.get(schedule=self)
        except Homework.DoesNotExist:
            hw = None

        if hw:
            hw_status = hw.get_status()
            hw_started = hw_status in ('в процессе', 'на проверке', 'выполнено')
            hw_done = hw_status == 'выполнено'
        else:
            hw_started = hw_done = False

        # --- Выбираем новый статус ---
        if theory_done and hw_done:
            new_status = self.STATUS_DONE
        elif theory_started or hw_started:
            new_status = self.STATUS_IN_PROGRESS
        else:
            new_status = self.STATUS_PENDING

        update_fields = []
        if new_status != self.status:
            self.status = new_status
            update_fields.append('status')

        if new_status == self.STATUS_DONE and not self.completed_at:
            self.completed_at = timezone.now()
            update_fields.append('completed_at')
        elif new_status != self.STATUS_DONE and self.completed_at is not None:
            self.completed_at = None
            update_fields.append('completed_at')

        if update_fields:
            self.save(update_fields=update_fields)
