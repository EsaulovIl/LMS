# onboarding/views.py
from datetime import datetime, timedelta
import random

from django.utils import timezone
from django.contrib import messages

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse

from .models import (
    SurveyQuestion, SurveyResponse,
    TestQuestion, TestResponse
)
from .forms import QuizForm, UnifiedSurveyForm, TestAnswerForm
from planning.services.plan_service import generate_personal_plan
from accounts.models import StudentGroup

# порядок шагов анкеты
SURVEY_STEPS = [
    'target_score',
    'weekly_hours',
    'start_date',
    'exam_date',
    'preferences',
    'preparation_priority'
]


@login_required
def survey_page(request):
    if request.method == 'POST':
        form = UnifiedSurveyForm(request.POST)
        if form.is_valid():
            # 1) Сначала удаляем все старые ответы
            SurveyResponse.objects.filter(user=request.user).delete()

            # 2) Обрабатываем want/know через getlist
            want_q = SurveyQuestion.objects.get(name='want_sections')
            know_q = SurveyQuestion.objects.get(name='know_sections')

            # здесь будут списки строковых id опций
            want_ids = request.POST.getlist('want_sections')
            know_ids = request.POST.getlist('know_sections')

            print("WANT IDS:", want_ids)
            print("KNOW IDS:", know_ids)

            for opt_id in want_ids:
                SurveyResponse.objects.create(
                    user=request.user,
                    question=want_q,
                    option_id=int(opt_id)
                )

            for opt_id in know_ids:
                SurveyResponse.objects.create(
                    user=request.user,
                    question=know_q,
                    option_id=int(opt_id)
                )

            # 3) Обрабатываем остальные поля формы
            for name, val in form.cleaned_data.items():
                if name in ('want_sections', 'know_sections', 'start_date'):
                    continue
                q = SurveyQuestion.objects.get(name=name)
                kwargs = {'user': request.user, 'question': q}
                if q.question_type == q.SINGLE:
                    kwargs['option_id'] = val
                elif q.question_type == q.NUMBER:
                    kwargs['value_number'] = val
                elif q.question_type == q.DECIMAL:
                    kwargs['value_decimal'] = val
                elif q.question_type == q.DATE:
                    kwargs['value_date'] = val
                else:
                    kwargs['value_text'] = val
                SurveyResponse.objects.create(**kwargs)

            # 4) Записываем дату начала
            start_q, _ = SurveyQuestion.objects.get_or_create(
                name='start_date',
                defaults={'text': 'Дата начала подготовки',
                          'question_type': SurveyQuestion.DATE,
                          'order': 99}
            )
            SurveyResponse.objects.update_or_create(
                user=request.user,
                question=start_q,
                defaults={'value_date': timezone.localdate()}
            )

            return redirect('onboarding:quiz_welcome')
    else:
        form = UnifiedSurveyForm()

    want_q = SurveyQuestion.objects.get(name='want_sections')
    sections = want_q.options.all()
    return render(request, 'onboarding/survey.html', {
        'form': form,
        'sections': sections,
    })


# ——— Тестирование ———

@login_required
def quiz_welcome(request):
    """
    Приветственная страница перед началом теста.
    """
    return render(request, 'onboarding/quiz_welcome.html')


@login_required
def quiz_start(request):
    TestResponse.objects.filter(user=request.user).delete()
    return redirect('onboarding:quiz_question', step=1)


@login_required
def quiz_question(request, step: int):
    questions = list(TestQuestion.objects.order_by('order'))
    total = len(questions)
    if step < 1 or step > total:
        return redirect('onboarding:quiz_finish')
    question = questions[step - 1]

    form = TestAnswerForm(request.POST or None, question=question)

    if request.method == 'POST' and 'save_answer' in request.POST:
        if form.is_valid():
            answer = form.cleaned_data['answer']
            TestResponse.objects.update_or_create(
                user=request.user,
                question=question,
                defaults={
                    'given_choice': answer if question.question_type == TestQuestion.THEORETICAL else None,
                    'given_answer': answer if question.question_type == TestQuestion.EGE1 else None,
                    'is_correct': question.is_correct(answer),
                    'submitted_at': timezone.now(),
                }
            )
            next_step = step + 1
            total = TestQuestion.objects.count()

            if next_step <= total:
                # редиректим на следующий вопрос
                return redirect('onboarding:quiz_question', step=next_step)
            else:
                # тестирование закончено — без параметров
                return redirect('onboarding:quiz_finish')

    # Инициализируем время старта теста (один раз)
    if 'quiz_start' not in request.session:
        request.session['quiz_start'] = timezone.now().timestamp()

    # Длительность экзамена: 3:55:00
    limit_seconds = 3 * 3600 + 55 * 60  # = 14 100 секунд

    # Уже прошедшее время
    elapsed = timezone.now().timestamp() - request.session['quiz_start']

    # Оставшееся время
    time_left = max(int(limit_seconds - elapsed), 0)

    indices = list(range(1, total + 1))
    return render(request, 'onboarding/quiz_question.html', {
        'question': question,
        'form': form,
        'step': step,
        'indices': indices,
        'time_left': time_left,
    })


@login_required
def quiz_finish(request):
    """
    Завершить тестирование — сгенерировать план и перенаправить студента
    на страницу «Мой курс». Если что-то пошло не так — показать ошибку.
    """
    try:
        # Генерируем персональный план для текущего студента
        plan = generate_personal_plan(request.user.id)
    except Exception as e:
        # Если алгоритм упал — покажем уведомление и уйдём на главную
        messages.error(
            request,
            f"Не удалось сформировать учебный план: {str(e)}"
        )
        return redirect('planning:home')

    # Привязываем студента к случайной группе с назначенным ментором
    available_groups = list(StudentGroup.objects.filter(mentor__isnull=False))
    if available_groups:
        group = random.choice(available_groups)
        group.students.add(request.user)
    # Всё ок — переходим сразу к своему курсу
    return redirect('planning:home')
