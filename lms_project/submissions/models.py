from django.db import models
from django.conf import settings
from courses.models import Section
from content.models import Theme

from utils.yadisk import get_yadisk_download_link


class SimilarityGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = 'SimilarityGroup'

    def __str__(self):
        return self.name


class Exercise(models.Model):
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='exercises'
    )
    theme = models.ForeignKey(
        Theme,
        on_delete=models.SET_NULL,
        null=True,
        related_name='exercises'
    )
    description = models.TextField(
        help_text="Markdown + LaTeX ($…$) для формулировки задачи"
    )
    complexity = models.IntegerField()
    exercise_type = models.CharField(max_length=20)  # 'test', 'open'
    created_at = models.DateTimeField(auto_now_add=True)

    # Новое поле: картинка, не обязательна
    image = models.ImageField(
        upload_to='exercise_images/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Одно изображение, относящееся к задаче"
    )

    # Новое поле: текст решения
    solution = models.TextField(
        null=True,
        blank=True,
        help_text="Описание решения в Markdown + LaTeX ($…$)"
    )

    correct_answer = models.TextField(
        null=True,
        blank=True,
        help_text="Правильный ответ для тестовых заданий (часть 1 ЕГЭ)"
    )

    similarity_group = models.ForeignKey(
        SimilarityGroup,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='exercises'
    )

    class Meta:
        db_table = 'Exercise'

    def __str__(self):
        return f"Упражнение #{self.pk} (секция {self.section_id})"


class Submission(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('auto-graded', 'Авто-оценено'),
        ('graded', 'Проверено'),
    ]

    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    grader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='graded_submissions'
    )
    answer = models.TextField(
        null=True, blank=True,
        help_text="Текст ответа пользователя"
    )

    score = models.IntegerField(
        null=True, blank=True,
        help_text="Первичные баллы, присвоенные за этот сабмит"
    )

    class Meta:
        db_table = 'Submission'
        ordering = ['-submitted_at']

    def __str__(self):
        return f"Submission #{self.pk} by {self.student.username}"

    @property
    def is_correct(self):
        """True, если пользовательский ответ совпадает с эталонным."""
        ca = (self.exercise.correct_answer or '').strip()
        ua = (self.answer or '').strip()
        return bool(ca and ua == ca)


class SubmissionFile(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='files')
    file_path = models.TextField()
    # полный путь на Яндекс.Диске
    disk_path = models.CharField(
        max_length=1024, null=True, blank=True,
        help_text="Путь на Яндекс.Диске"
    )
    # прямой download-URL
    content_url = models.TextField(
        null=True, blank=True,
        help_text="Прямая ссылка на скачивание"
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'SubmissionFile'

    def __str__(self):
        return f"File #{self.pk} for Submission #{self.submission_id}"

    def save(self, *args, **kwargs):
        # если есть путь на диске — обновляем ссылку
        if self.disk_path:
            try:
                self.content_url = get_yadisk_download_link(self.disk_path)
            except Exception:
                # можно логировать ошибку, но не мешать сохранению
                pass
        super().save(*args, **kwargs)


class SubmissionFeedback(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name='feedbacks')
    mentor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feedbacks')
    feedback = models.TextField()
    grade = models.IntegerField()  # первичные баллы согласно критериям
    file_path = models.CharField(max_length=255, null=True, blank=True)
    disk_path = models.CharField(max_length=1024, null=True, blank=True)
    content_url = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'SubmissionFeedback'

    def __str__(self):
        return f"Feedback #{self.pk} for Submission #{self.submission_id}"
