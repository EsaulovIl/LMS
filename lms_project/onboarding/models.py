from django.db import models
from django.conf import settings
from courses.models import Section


# --- Анкета ---

class SurveyQuestion(models.Model):
    TEXT, NUMBER, DECIMAL, DATE, SINGLE, MULTIPLE = (
        'text', 'number', 'decimal', 'date', 'single', 'multiple'
    )
    QUESTION_TYPES = [
        (TEXT, 'Текст'),
        (NUMBER, 'Число (целое)'),
        (DECIMAL, 'Число (дробное)'),
        (DATE, 'Дата'),
        (SINGLE, 'Один выбор'),
        (MULTIPLE, 'Несколько выбор'),
    ]
    name = models.SlugField(unique=True)
    text = models.TextField()
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPES)
    min_value = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2)
    max_value = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'SurveyQuestion'
        ordering = ['order']


class SurveyOption(models.Model):
    question = models.ForeignKey(SurveyQuestion, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=255)
    value = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'SurveyOption'


class SurveyResponse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             related_name='survey_responses')
    question = models.ForeignKey(SurveyQuestion,
                                 on_delete=models.CASCADE,
                                 related_name='responses')
    option = models.ForeignKey(SurveyOption, null=True, blank=True,
                               on_delete=models.CASCADE)
    value_text = models.TextField(null=True, blank=True)
    value_number = models.IntegerField(null=True, blank=True)
    value_decimal = models.DecimalField(null=True, blank=True, max_digits=5, decimal_places=2)
    value_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'SurveyResponse'
        unique_together = [('user', 'question', 'option')]


# --- Тестирование ---

class TestQuestion(models.Model):
    THEORETICAL = 'theoretical'
    EGE1 = 'ege1'
    TYPE_CHOICES = [(THEORETICAL, 'Теоретический'), (EGE1, 'ЕГЭ-1')]
    question_text = models.TextField()
    question_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    choice_a = models.CharField(max_length=255, blank=True, null=True)
    choice_b = models.CharField(max_length=255, blank=True, null=True)
    choice_c = models.CharField(max_length=255, blank=True, null=True)
    choice_d = models.CharField(max_length=255, blank=True, null=True)
    correct_choice = models.CharField(max_length=1, choices=[(c, c) for c in ('A', 'B', 'C', 'D')],
                                      blank=True, null=True)
    image = models.ImageField(upload_to='ege1_images/', blank=True, null=True)
    correct_answer = models.CharField(max_length=255, blank=True, null=True)
    # привязка к разделу
    section = models.ForeignKey(
        Section,
        on_delete = models.CASCADE,
        related_name = 'test_questions',
        help_text = "Раздел ЕГЭ, к которому относится вопрос"
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'TestQuestion'
        ordering = ['order']

    def is_correct(self, answer):
        if self.question_type == self.THEORETICAL:
            return answer == self.correct_choice
        return str(answer).strip() == str(self.correct_answer or '').strip()


class TestResponse(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE,
                             related_name='test_responses')
    question = models.ForeignKey(TestQuestion,
                                 on_delete=models.CASCADE,
                                 related_name='responses')
    given_choice = models.CharField(max_length=1, blank=True, null=True)
    given_answer = models.CharField(max_length=255, blank=True, null=True)
    is_correct = models.BooleanField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'TestResponse'
        unique_together = [('user', 'question')]
