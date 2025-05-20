from django.db import models
from django.conf import settings

from submissions.models import Exercise
from content.models import Theme


class PracticeAssignment(models.Model):
    """
    Отработка — набор упражнений, которые студент плохо решил.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='practice_assignments'
    )

    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Когда была назначена отработка"
    )

    deadline = models.DateField()

    # упражнения через промежуточную таблицу
    exercises = models.ManyToManyField(
        Exercise,
        through='PracticeAssignmentExercise',
        related_name='practice_assignments'
    )

    theme = models.ForeignKey(
        Theme,
        on_delete=models.CASCADE,
        related_name='practice_assignments',
        help_text="Тема, к которой относится эта отработка"
    )

    class Meta:
        db_table = 'PracticeAssignment'
        ordering = ['-assigned_at']

    def __str__(self):
        return f"Отработка #{self.pk} для {self.student.username}"

    @property
    def total_score(self):
        from django.db.models import Sum
        res = self.ex_links.aggregate(total=Sum('grade'))['total']
        return res or 0


class PracticeAssignmentExercise(models.Model):
    PENDING = 'pending'
    AUTO_GRADED = 'auto-graded'
    GRADED = 'graded'

    STATUS_CHOICES = [(PENDING, 'В ожидании'),(AUTO_GRADED, 'Авто-оценено'),(GRADED, 'Проверено'),]

    assignment = models.ForeignKey(
        PracticeAssignment,
        on_delete=models.CASCADE,
        related_name='ex_links'
    )
    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE
    )
    grade = models.IntegerField(
        null=True,
        blank=True,
        help_text='Баллы, выставленные за это упражнение; NULL — ещё не проверено'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        help_text='Статус проверки упражнения'
    )

    class Meta:
        db_table = 'PracticeAssignmentExercise'
        unique_together = ('assignment', 'exercise')

    def __str__(self):
        return f"Отраб#{self.assignment_id}–Ex#{self.exercise_id}: {self.grade}"
