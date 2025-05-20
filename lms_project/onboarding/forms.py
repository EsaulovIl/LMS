from django import forms
from .models import SurveyQuestion, TestQuestion


class UnifiedSurveyForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Загружаем все вопросы, кроме start_date
        questions = SurveyQuestion.objects.exclude(name='start_date').order_by('order')
        for q in questions:
            field_name = q.name
            if q.question_type == SurveyQuestion.SINGLE:
                choices = [(opt.pk, opt.text) for opt in q.options.all()]
                self.fields[field_name] = forms.ChoiceField(
                    label=q.text, choices=choices, widget=forms.Select
                )
            elif q.question_type == SurveyQuestion.MULTIPLE:
                choices = [(opt.value, opt.text) for opt in q.options.all()]
                # here we want two separate fields: one for "want", one for "know"
                # we'll name them exactly "want_sections" and "know_sections"
                if field_name == 'topics_know':
                    self.fields['want_sections'] = forms.MultipleChoiceField(
                        label='Хочу разбирать',
                        choices=choices,
                        widget=forms.CheckboxSelectMultiple,
                        required=False
                    )
                    self.fields['know_sections'] = forms.MultipleChoiceField(
                        label='Умею решать',
                        choices=choices,
                        widget=forms.CheckboxSelectMultiple,
                        required=False
                    )
            elif q.question_type == SurveyQuestion.NUMBER:
                self.fields[field_name] = forms.IntegerField(label=q.text,
                                                             min_value=int(q.min_value or 0),
                                                             max_value=int(q.max_value or 100))
            elif q.question_type == SurveyQuestion.DECIMAL:
                self.fields[field_name] = forms.DecimalField(label=q.text,
                                                             min_value=q.min_value, max_value=q.max_value,
                                                             decimal_places=2)
            elif q.question_type == SurveyQuestion.DATE:
                self.fields[field_name] = forms.DateField(label=q.text, widget=forms.DateInput)
            else:  # TEXT
                self.fields[field_name] = forms.CharField(label=q.text, widget=forms.Textarea)


class QuizForm(forms.Form):
    def __init__(self, *args, question: TestQuestion, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question
        if question.question_type == question.THEORETICAL:
            choices = [
                ('A', question.choice_a),
                ('B', question.choice_b),
                ('C', question.choice_c),
                ('D', question.choice_d),
            ]
            self.fields['answer'] = forms.ChoiceField(
                label=question.question_text,
                choices=choices,
                widget=forms.RadioSelect
            )
        else:
            self.fields['answer'] = forms.CharField(
                label=question.question_text,
                widget=forms.TextInput(attrs={'autocomplete': 'off'})
            )


class TestAnswerForm(forms.Form):
    answer = forms.CharField(label='Ваш ответ')

    def __init__(self, *args, question: TestQuestion, **kwargs):
        super().__init__(*args, **kwargs)
        self.question = question

        if question.question_type == TestQuestion.THEORETICAL:
            choices = [
                ('A', question.choice_a),
                ('B', question.choice_b),
                ('C', question.choice_c),
                ('D', question.choice_d),
            ]
            self.fields['answer'] = forms.ChoiceField(
                label='Ваш вариант',
                choices=choices,
                widget=forms.RadioSelect
            )

        elif question.question_type == TestQuestion.EGE1:
            # Оставляем текстовое поле, можно ограничить ввод числом
            self.fields['answer'] = forms.CharField(
                label='Ваш ответ',
                widget=forms.TextInput(attrs={'autocomplete': 'off'})
            )
        # иначе — текстовое поле по умолчанию
