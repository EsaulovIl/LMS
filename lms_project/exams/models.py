from django.db import models
from django.conf import settings
from courses.models import Section
from submissions.models import Exercise


class ExamVariant(models.Model):
    name = models.CharField(max_length=100)
    deadline = models.DateTimeField()

    class Meta:
        db_table = 'ExamVariant'
        ordering = ['deadline']

    def __str__(self):
        return self.name


class StudentExam(models.Model):
    variant = models.ForeignKey(ExamVariant, on_delete=models.CASCADE, related_name='student_exams')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_exams')
    assigned_at = models.DateTimeField(auto_now_add=True)
    deadline = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'StudentExam'
        unique_together = ('variant', 'student')
        ordering = ['-assigned_at']

    def __str__(self):
        return f"{self.student.username} — {self.variant.name}"

    @property
    def status(self):
        """
        in_progress     — экзамен ещё не завершён (completed_at is None)
        pending_review  — экзамен завершён, но есть open-задания без оценки
        graded          — все open-задания оценены (или их нет)
        """

        if not self.completed_at:
            return 'in_progress'
        # Считаем, сколько open-заданий в самом экзамене
        total_open = self.exam_exercises.filter(
            exercise__exercise_type = 'open'
        ).count()
        if total_open == 0:
            # нет открытых заданий — считаем всё проверенным
            return 'graded'
        # Сколько уникальных open-упражнений уже получили статус 'graded'
        reviewed = self.submissions.filter(
            exercise__exercise_type = 'open',
            status = 'graded'
        ).values('exercise').distinct().count()

        if reviewed < total_open:
            return 'pending_review'


        return 'graded'


class StudentExamExercise(models.Model):
    exam = models.ForeignKey(StudentExam, on_delete=models.CASCADE, related_name='exam_exercises')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    order_idx = models.PositiveIntegerField()

    class Meta:
        db_table = 'StudentExamExercise'
        unique_together = ('exam', 'order_idx')
        ordering = ['order_idx']

    def __str__(self):
        return f"Exam #{self.exam_id} — #{self.order_idx}"


class ExamSubmission(models.Model):
    exam = models.ForeignKey(StudentExam, on_delete=models.CASCADE, related_name='submissions')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE)
    submitted_at = models.DateTimeField(auto_now_add=True)
    answer = models.TextField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'В ожидании'),
            ('auto-graded', 'Авто-оценено'),
            ('graded', 'Проверено'),
        ],
        default='pending'
    )
    grader = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='exam_feedbacks'
    )
    grade = models.IntegerField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'ExamSubmission'
        unique_together = ('exam', 'exercise')
        ordering = ['submitted_at']

    def __str__(self):
        return f"ExamSubm #{self.pk} ({self.exam.student.username} → {self.exercise.pk})"


class ExamSubmissionFile(models.Model):
    exam_submission = models.ForeignKey(
        ExamSubmission, on_delete=models.CASCADE, related_name='files'
    )
    file_name = models.CharField(max_length=255)
    disk_path = models.TextField()
    content_url = models.TextField()
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ExamSubmissionFile'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"File {self.file_name} for Subm#{self.exam_submission_id}"


class ExamSubmissionFeedback(models.Model):
    """
    Обратная связь ментора по одному упражнению второй части пробного экзамена.
    """
    # Связываем с записью StudentExamExercise (упражнение внутри экзамена)
    exam_exercise = models.ForeignKey(
        'exams.StudentExamExercise',
        on_delete=models.CASCADE,
        related_name='feedbacks'
    )
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='exam_exercise_feedbacks'
    )
    feedback = models.TextField(help_text="Комментарий ментора")
    grade = models.IntegerField(help_text="Баллы по критериям ЕГЭ для этой части")

    # Поля для файла решения ментора (по аналогии с SubmissionFeedback)
    file_path = models.CharField(max_length=255, null=True, blank=True)
    disk_path = models.CharField(max_length=1024, null=True, blank=True)
    content_url = models.TextField(null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ExamSubmissionFeedback'
        verbose_name = "Обратная связь по упражнению экзамена"
        verbose_name_plural = "Обратная связь по упражнениям экзамена"

    def __str__(self):
        return f"Feedback #{self.pk} for ExamExercise #{self.exam_exercise_id}"
