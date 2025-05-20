from django.db import models
from django.utils import timezone
from django.conf import settings

from planning.models import ThemeSchedule
from submissions.models import Exercise, Submission


class Homework(models.Model):
    """
    Домашнее задание по теме: выдано в assigned_at, дедлайн — в deadline.
    Состав упражнений через связь HomeworkExercise.
    """
    schedule = models.OneToOneField(
        ThemeSchedule,
        on_delete=models.CASCADE,
        related_name='homework'
    )
    assigned_at = models.DateTimeField(default=timezone.now)
    deadline = models.DateField()

    # связь ManyToMany через промежуточную модель
    exercises = models.ManyToManyField(
        Exercise,
        through='HomeworkExercise',
        related_name='homeworks'
    )

    class Meta:
        db_table = 'Homework'
        ordering = ['-assigned_at']

    def __str__(self):
        return f"HW#{self.pk} [{self.theme.name}]"

    @property
    def theme(self):
        return self.schedule.theme

    def get_status(self) -> str:
        """
        Возвращает один из статусов:
        - 'выполнено' — все тесты и все open-задания проверены (graded),
                          или open-заданий изначально нет
        - 'на проверке' — все тесты auto|graded и все open-задания сданы,
                          но ещё не все graded
        - 'в процессе' — есть хотя бы одна выполненная задача
        - 'не начато' — нет ни одного выполненного сабмита
        """
        # 1) получаем все привязки к упражнениям
        hw_exs = self.ex_link.select_related('exercise').all()

        # 2) разделяем на тестовые и open
        test_qs = hw_exs.filter(exercise__exercise_type='test')
        open_qs = hw_exs.exclude(exercise__exercise_type='test')

        # 3) считаем тесты
        test_total = test_qs.count()
        test_done = test_qs.filter(
            status__in=[
                HomeworkExercise.AUTO_GRADED,
                HomeworkExercise.GRADED
            ]
        ).count()

        # 4) считаем open
        open_total = open_qs.count()
        open_graded = open_qs.filter(
            status=HomeworkExercise.GRADED
        ).count()

        # 5) считаем, сколько open сданы (есть хотя бы один Submission)
        student = self.schedule.plan.student
        submitted_open = Submission.objects.filter(
            student=student,
            exercise__in=open_qs.values_list('exercise', flat=True)
        ).values('exercise').distinct().count()

        # 6) логика статусов
        # — Выполнено: все тесты и все open (если они есть) graded
        if test_done == test_total and (open_total == 0 or open_graded == open_total):
            return 'выполнено'

        # — На проверке: все тесты авто-оценены/graded, все open сданы, но не все graded
        if test_done == test_total and open_total > 0 and submitted_open == open_total:
            return 'на проверке'

        # — В процессе: хотя бы один тест auto-оценён или хотя бы один open сдан
        if test_done + submitted_open > 0:
            return 'в процессе'

        # — Не начато
        return 'не начато'


"""
    @property
    def total_score(self):
        from django.db.models import Sum
        agg = self.exercises_link.aggregate(total=Sum('grade'))
        return agg['total'] or 0

    @property
    def max_score(self):
        # Предполагаем, что в Exercise есть поле max_score
        from django.db.models import Sum
        agg = self.exercises_link.aggregate(
            total=Sum('exercise__max_score')
        )
        return agg['total'] or 0

    @property
    def score_ratio(self):
        max_ = self.max_score
        return (self.total_score / max_) if max_ else 0
"""


class HomeworkExercise(models.Model):
    """
    Промежуточная таблица: к какой HW привязано какое упражнение,
    и сколько студент набрал баллов за него.
    """
    PENDING = 'pending'
    AUTO_GRADED = 'auto-graded'
    GRADED = 'graded'

    STATUS_CHOICES = [
        (PENDING, 'В ожидании'),
        (AUTO_GRADED, 'Авто-оценено'),
        (GRADED, 'Проверено'),
    ]
    homework = models.ForeignKey(
        Homework,
        on_delete=models.CASCADE,
        related_name='ex_link'
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
        db_table = 'HomeworkExercise'
        unique_together = ('homework', 'exercise')

    def __str__(self):
        return f"HW#{self.homework_id}–Ex#{self.exercise_id}: {self.grade}"
