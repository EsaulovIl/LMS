from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class Role(models.Model):
    name = models.CharField(
        max_length=30,
        unique=True,
        # help_text="student, mentor, teacher, admin"
    )

    class Meta:
        db_table = 'Role'
        # managed = False

    def __str__(self):
        return self.name


class User(AbstractUser):
    # Переопределяем поле password, чтобы оно шло в колонку password_hash
    password = models.CharField(
        _('password'),
        max_length=128,
        db_column='password_hash'
    )
    email = models.EmailField(_('email address'), unique=True)
    phone_number = models.CharField(max_length=20)
    role = models.ForeignKey(
        Role,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'User'
        # managed = False


class Notification(models.Model):
    """
    Уведомление для пользователя.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'Notification'
        ordering = ['-created_at']

    def mark_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save()


class MentorManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role__name='mentor')


class StudentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(role__name='student')


class Mentor(User):
    objects = MentorManager()

    class Meta:
        proxy = True
        verbose_name = 'Ментор'
        verbose_name_plural = 'Менторы'


class Student(User):
    objects = StudentManager()

    class Meta:
        proxy = True
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'

class StudentGroup(models.Model):
    """
    Группа студентов под кураторством одного ментора.
    """
    name = models.CharField("Название группы", max_length=100)
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mentored_groups",
        limit_choices_to={'role__name': 'mentor'},
        verbose_name="Ментор"
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="student_groups",
        limit_choices_to={'role__name': 'student'},
        blank=True,
        verbose_name="Студенты"
    )

    class Meta:
        db_table = 'StudentGroup'
        verbose_name = "Группа студентов"
        verbose_name_plural = "Группы студентов"

    def __str__(self):
        return f"{self.name} ({self.mentor.get_full_name() or self.mentor.username})"