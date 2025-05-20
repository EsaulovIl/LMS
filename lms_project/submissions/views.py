# apps/submissions/views.py

from django import forms
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from homework.models import Homework, HomeworkExercise
from practice.models import PracticeAssignment
from .models import Exercise, Submission, SubmissionFile, SubmissionFeedback
from content.models import Notebook
from .utils import upload_file_to_yadisk, get_student_mentor


class AnswerForm(forms.Form):
    answer = forms.CharField(
        label='Ваш ответ',
        widget=forms.TextInput(attrs={'autocomplete': 'off'})
    )


class FileAnswerForm(forms.Form):
    file = forms.FileField(label='Прикрепить файл решения')


@login_required
def solve_exercise(request, assignment_id, exercise_id):
    # Определяем контекст: домашка или практика ---
    hw_ex = HomeworkExercise.objects.filter(
        homework_id=assignment_id,
        homework__schedule__plan__student=request.user,
        exercise_id=exercise_id
    ).select_related('homework').first()

    if hw_ex:
        assignment_type = 'homework'
        assignment = hw_ex.homework
    else:
        # убеждаемся, что это отработка и упражнение там есть
        pa = get_object_or_404(
            PracticeAssignment,
            pk=assignment_id,
            student=request.user,
            ex_links__exercise_id=exercise_id
        )
        assignment_type = 'practice'
        assignment = pa

    exercise = get_object_or_404(Exercise, pk=exercise_id)

    # --- 1. Последний сабмит (auto-graded / pending / graded) ---
    last_sub = Submission.objects.filter(
        student=request.user,
        exercise=exercise,
        status__in=['auto-graded', 'pending', 'graded']
    ).order_by('-submitted_at').first()

    # По умолчанию обе формы пусты
    text_form = None
    file_form = None
    feedbacks = []

    # === 2. Часть 1: тестовые упражнения ===
    if exercise.exercise_type == 'test':
        if last_sub and last_sub.status == 'auto-graded':
            # ничего не делаем — просто покажем результат
            pass
        elif request.method == 'POST':
            text_form = AnswerForm(request.POST)
            if text_form.is_valid():
                submission = Submission.objects.create(
                    exercise=exercise,
                    student=request.user,
                    answer=text_form.cleaned_data['answer'].strip(),
                    status='auto-graded',
                    grader=None
                )
                last_sub = submission
                text_form = None
        else:
            text_form = AnswerForm()

    # === 3. Часть 2: открытые упражнения ===
    else:
        # 3.1. Если уже graded — сразу собираем фидбэк
        if last_sub and last_sub.status == 'graded':
            feedbacks = SubmissionFeedback.objects.filter(submission=last_sub)
        # 3.2. Если POST и нет сабмита или он в pending — загружаем файл
        elif request.method == 'POST':
            file_form = FileAnswerForm(request.POST, request.FILES)
            if file_form.is_valid():
                f = file_form.cleaned_data['file']
                disk_path, content_url = upload_file_to_yadisk(
                    f,
                    request.user.id,
                    assignment_type,
                    assignment.pk,
                    exercise.pk
                )
                mentor = get_student_mentor(request.user.id)
                submission = Submission.objects.create(
                    exercise=exercise,
                    student=request.user,
                    answer='',
                    status='pending',
                    grader=mentor
                )
                SubmissionFile.objects.create(
                    submission=submission,
                    file_path=f.name,
                    disk_path=disk_path,
                    content_url=content_url
                )
                last_sub = submission
                # после загрузки формы оставляем новую пустую форму,
                # чтобы снова можно было перезагрузить решение, пока не graded
                file_form = FileAnswerForm()
        else:
            # GET — если ещё нет сабмита или он в pending, показываем форму
            if not last_sub or last_sub.status == 'pending':
                file_form = FileAnswerForm()

    # === 4. Навигация по упражнениям ===
    if assignment_type == 'homework':
        ex_ids = list(assignment.exercises.order_by('pk')
                      .values_list('pk', flat=True))
    else:
        ex_ids = [ln.exercise_id for ln in assignment.ex_links.order_by('exercise_id')]

    idx = ex_ids.index(exercise.pk)
    prev_id = ex_ids[idx - 1] if idx > 0 else None
    next_id = ex_ids[idx + 1] if idx < len(ex_ids) - 1 else None

    # === 5. Материалы по теме ===
    notebooks = Notebook.objects.filter(theme=exercise.theme)

    return render(request, 'submissions/solve.html', {
        'assignment_type': assignment_type,
        'assignment': assignment,
        'exercise': exercise,
        'submission': last_sub,
        'form': text_form,
        'file_form': file_form,
        'feedbacks': feedbacks,
        'ex_ids': ex_ids,
        'current_id': exercise.pk,
        'prev_id': prev_id,
        'next_id': next_id,
        'notebooks': notebooks,
    })


@login_required
def view_solution(request, assignment_id, exercise_id):
    """
    Показывает пояснение к задаче, если последний автосабмит был неверным.
    Кнопка «← Назад» ведёт на домашку или практику, откуда пришли.
    """
    # Подгружаем контекст
    hw = Homework.objects.filter(
        pk=assignment_id,
        schedule__plan__student=request.user,
        exercises__pk=exercise_id
    ).first()
    if hw:
        assignment_type = 'homework'
        assignment = hw
    else:
        pa = get_object_or_404(
            PracticeAssignment,
            pk=assignment_id,
            student=request.user,
            exercises__pk=exercise_id
        )
        assignment_type = 'practice'
        assignment = pa

    # Упражнение + последний автосабмит
    exercise = get_object_or_404(Exercise, pk=exercise_id)
    sub_qs = Submission.objects.filter(
        student=request.user,
        exercise=exercise
    ).order_by('-submitted_at')

    if exercise.exercise_type == 'test':
        # тестовое: берём последний auto-graded
        sub = sub_qs.filter(status='auto-graded').first()
        if not sub:
            raise Http404("Нет автопроверенного сабмита для тестового задания.")
        # проверяем корректность и подтягиваем пояснение из exercise.solution
        correct = (sub.answer.strip() == (exercise.correct_answer or '').strip())
        context = {
            'assignment_type': assignment_type,
            'assignment': assignment,
            'exercise': exercise,
            'submission': sub,
            'correct': correct,
            'notebooks': Notebook.objects.filter(theme=exercise.theme),
        }
        return render(request, 'submissions/solution.html', context)

    else:
        # открытое (часть 2): берём последний pending или graded
        sub = sub_qs.filter(status__in=['pending', 'graded']).first()
        if not sub:
            raise Http404("Задание ещё не отправлено или не найдено.")
        # подтягиваем все фидбэки от ментора
        feedbacks = SubmissionFeedback.objects.filter(submission=sub).order_by('created_at')
        # собираем файлы решения ментора, текст и оценку
        # (в шаблоне можно итерировать feedbacks и выводить поля .feedback, .grade, .content_url)
        context = {
            'assignment_type': assignment_type,
            'assignment': assignment,
            'exercise': exercise,
            'submission': sub,
            'feedbacks': feedbacks,
            'notebooks': Notebook.objects.filter(theme=exercise.theme),
        }
        return render(request, 'submissions/solution.html', context)
