from django.db import models
from django.conf import settings
from courses.models import Section
from utils.yadisk import get_yadisk_download_link
import logging

logger = logging.getLogger(__name__)

class Theme(models.Model):
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name='themes'
    )
    name = models.CharField(max_length=200)
    complexity = models.IntegerField()
    priority = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Themes'
        ordering = ['section__id', 'id']

    def __str__(self):
        return f"{self.section.name} → {self.name}"


class Notebook(models.Model):
    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='notebooks'
    )
    title = models.CharField(max_length=200)
    disk_path = models.TextField(
        help_text="Путь на Яндекс.Диске: /lms_media/notebooks/..."
    )
    content_url = models.URLField(
        blank=True,
        help_text="Прямая ссылка на скачивание (обновляется автоматически)"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Notebooks'
        ordering = ['uploaded_at']

    def save(self, *args, **kwargs):
        if self.disk_path:
            try:
                url = get_yadisk_download_link(self.disk_path)
                logger.debug(f"[Notebook.save] got URL for '{self.disk_path}': {url}")
                self.content_url = url
            except Exception as e:
                logger.error(f"[Notebook.save] error for '{self.disk_path}': {e}")
        else:
            logger.warning("[Notebook.save] disk_path is empty")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.theme.name} — {self.title}"


class VideoLesson(models.Model):
    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='video_lessons'
    )
    title = models.CharField(max_length=200)
    disk_path = models.TextField(
        help_text="Путь на Яндекс.Диске: /lms_media/videos/..."
    )
    video_url = models.URLField(
        blank=True,
        help_text="Прямая ссылка на видео (обновляется автоматически)"
    )
    duration = models.DurationField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'VideoLesson'
        ordering = ['uploaded_at']

    def save(self, *args, **kwargs):
        # при каждом сохранении обновляем video_url
        if self.disk_path:
            try:
                self.video_url = get_yadisk_download_link(self.disk_path)
            except Exception as e:
                # логируем, но не мешаем сохранить модель
                import logging
                logging.getLogger(__name__).error(
                    f"YDisk error for {self.disk_path}: {e}"
                )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.theme.name} — {self.title}"


class VideoProgress(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='video_progress'
    )
    video = models.ForeignKey(
        VideoLesson,
        on_delete=models.CASCADE,
        related_name='progress'
    )
    watched_percent = models.FloatField(default=0)
    last_watched_at = models.DateTimeField(auto_now=True)

    viewed = models.BooleanField(
        default = False,
        help_text = "True, когда просмотр ≥100%, и не сбрасывается"
    )

    class Meta:
        db_table = 'VideoProgress'
        unique_together = ('student', 'video')

    def __str__(self):
        return f"{self.student.username} — {self.video.title}: {self.watched_percent:.0f}%"
