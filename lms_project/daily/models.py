from django.db import models
from django.conf import settings


class DailyQuizTask(models.Model):
    question = models.TextField()
    explanation = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'DailyQuizTask'


class DailyQuizOption(models.Model):
    task = models.ForeignKey(DailyQuizTask, on_delete=models.CASCADE, related_name='options')
    option_text = models.TextField()
    is_correct = models.BooleanField(default=False)

    class Meta:
        db_table = 'DailyQuizOption'


class DailyQuizAssignment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_assignments')
    task = models.ForeignKey(DailyQuizTask, on_delete=models.CASCADE)
    assigned_date = models.DateField()
    selected_option = models.ForeignKey(DailyQuizOption, null=True, blank=True, on_delete=models.SET_NULL)
    is_correct = models.BooleanField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'DailyQuizAssignment'
        unique_together = ('user', 'assigned_date')
