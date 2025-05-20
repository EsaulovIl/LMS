# submissions/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver

from submissions.models import Submission
from homework.models import HomeworkExercise
from practice.models import PracticeAssignmentExercise

@receiver(post_save, sender=Submission)
def propagate_submission_score(sender, instance, **kwargs):
    """
    При любом сохранении сабмита дублируем score и status
    в HomeworkExercise или PracticeExercise (в зависимости от того,
    откуда пришла попытка).
    """
    student = instance.student
    exercise = instance.exercise
    score_val = instance.score
    status_val = instance.status

    # --- Домашка ---
    try:
        hw_ex = HomeworkExercise.objects.get(
            homework__schedule__plan__student=student,
            exercise=exercise
        )
    except HomeworkExercise.DoesNotExist:
        hw_ex = None

    if hw_ex:
        hw_ex.grade  = score_val
        hw_ex.status = status_val
        hw_ex.save(update_fields=['grade', 'status'])
        return

    # --- Практика ---
    try:
        pr_ex = PracticeAssignmentExercise.objects.get(
            assignment__student=student,
            exercise=exercise
        )
    except PracticeAssignmentExercise.DoesNotExist:
        pr_ex = None

    if pr_ex:
        pr_ex.grade  = score_val
        pr_ex.status = status_val
        pr_ex.save(update_fields=['grade', 'status'])
