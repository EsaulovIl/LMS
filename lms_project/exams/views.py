import random
from datetime import datetime, date
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
from django import forms
from django.contrib import messages

from courses.models import Section
from submissions.views import AnswerForm
from submissions.utils import upload_file_to_yadisk, get_student_mentor

from .models import (
    ExamVariant,
    StudentExam,
    StudentExamExercise,
    ExamSubmission,
    ExamSubmissionFile
)


@login_required
def exam_list(request):
    variants = ExamVariant.objects.all()
    today = date(2025, 5, 8)

    existing = {se.variant_id: se for se in request.user.student_exams.all()}
    upcoming, completed = [], []

    for variant in variants:
        se = existing.get(variant.id)
        if not se:
            se = StudentExam.objects.create(
                variant=variant,
                student=request.user,
                deadline=variant.deadline
            )
            # рандомно по одному упражнению из каждого раздела
            idx = 1
            for sec in Section.objects.all().order_by('id'):
                qs = sec.exercises.all()
                if qs.exists():
                    ex = random.choice(list(qs))
                    StudentExamExercise.objects.create(
                        exam=se, exercise=ex, order_idx=idx
                    )
                    idx += 1

        if se.completed_at:
            # в завершённых нам days_left не нужен
            se.days_left = None
            completed.append(se)
        else:
            # считаем дни до дедлайна
            # deadline — это DateTimeField, но сравниваем по дате
            delta = se.deadline.date() - today
            se.days_left = delta.days
            upcoming.append(se)

    return render(request, 'exams/list.html', {
        'today_date': today,
        'upcoming': upcoming,
        'completed': completed,
    })


class FileAnswerForm(forms.Form):
    file = forms.FileField(label='Файл решения')


@login_required
def exam_detail(request, exam_id):
    # 1) Найти свой StudentExam
    se = get_object_or_404(StudentExam, pk=exam_id, student=request.user)

    # 2) Если у него ещё нет упражнений — создаём их
    if se.exam_exercises.count() == 0:
        idx = 1
        for sec in Section.objects.order_by('id'):
            qs = sec.exercises.all()
            if not qs.exists():
                continue
            ex = random.choice(list(qs))
            StudentExamExercise.objects.create(
                exam=se,
                exercise=ex,
                order_idx=idx
            )
            idx += 1

    # --- инициализируем время старта и лимит ---
    NOW = timezone.now()
    if se.start_time is None:
        se.start_time = NOW
        se.save(update_fields=['start_time'])
        # инициализируем ExamSubmission для каждого упражнения
        mentor = get_student_mentor(request.user.id)
        for link in se.exam_exercises.all():
            defaults = {
                'status': 'pending',
                # если это часть 2 и есть ментор — сразу назначаем
                'grader': mentor if link.exercise.exercise_type == 'open' else None
            }
            ExamSubmission.objects.get_or_create(
                exam=se,
                exercise=link.exercise,
                defaults=defaults
            )
    # лимит = 3 часа 55 минут
    END = se.start_time + timedelta(hours=3, minutes=55)
    # если время вышло — автоматически завершаем
    if NOW >= END and not se.completed_at:
        se.completed_at = NOW
        se.save(update_fields=['completed_at'])
        return redirect('exams:list')

    # --- навигация по упражнениям ---
    total = se.exam_exercises.count()
    try:
        idx = int(request.GET.get('q', 1))
    except (TypeError, ValueError):
        idx = 1
    idx = max(1, min(idx, total))
    prev_idx = idx - 1 if idx > 1 else None
    next_idx = idx + 1 if idx < total else None
    indices = list(range(1, total + 1))

    # текущее упражнение
    link = se.exam_exercises.get(order_idx=idx)
    exercise = link.exercise

    # получаем или создаём черновик ExamSubmission
    sub, created = ExamSubmission.objects.get_or_create(
        exam=se,
        exercise=exercise,
        defaults={
            'status': 'pending',
            'grader': get_student_mentor(request.user.id)
        }
    )

    # --- обработка сохранения черновика ---
    if request.method == 'POST':
        # Сохраняем ответ для test
        if 'save_answer' in request.POST and exercise.exercise_type == 'test':
            form = AnswerForm(request.POST)
            if form.is_valid():
                sub.answer = form.cleaned_data['answer'].strip()
                sub.save()
                return redirect(f"{request.path}?q={idx}")

        # Сохранить/заменить файл для open
        if 'save_file' in request.POST and exercise.exercise_type != 'test':
            file_form = FileAnswerForm(request.POST, request.FILES)
            if file_form.is_valid():
                f = file_form.cleaned_data['file']
                # удалить старые файлы
                sub.files.all().delete()
                # загрузить на Я.Диск
                disk_path, content_url = upload_file_to_yadisk(
                    f,
                    request.user.id,
                    'exam',
                    se.pk,
                    exercise.pk
                )
                # сохранить запись о файле
                ExamSubmissionFile.objects.create(
                    exam_submission=sub,
                    file_name=f.name,
                    disk_path=disk_path,
                    content_url=content_url
                )
                return redirect(f"{request.path}?q={idx}")

    # формы для шаблона
    answer_form = AnswerForm(initial={'answer': sub.answer}) if exercise.exercise_type == 'test' else None
    file_form = FileAnswerForm() if exercise.exercise_type != 'test' else None

    # Вычисляем оставшееся время в секундах
    time_left = max(int((END - NOW).total_seconds()), 0)

    return render(request, 'exams/detail.html', {
        'exam': se,
        'exercise': exercise,
        'sub': sub,
        'answer_form': answer_form,
        'file_form': file_form,
        'idx': idx,
        'prev_idx': prev_idx,
        'next_idx': next_idx,
        'total': total,
        'indices': indices,
        'time_left': time_left,
    })


@login_required
def exam_results(request, exam_id):
    se = get_object_or_404(StudentExam, pk=exam_id, student=request.user)

    # Разрешаем только после полной проверки
    if se.status != 'graded':
        messages.error(request, "Результаты будут доступны после проверки всех заданий второй части.")
        return redirect('exams:detail', exam_id)

    # Словарь exercise_id → ExamSubmission
    subs_qs = ExamSubmission.objects.filter(exam=se).select_related('exercise__section')
    subs_map = {sub.exercise_id: sub for sub in subs_qs}

    # Проходим по порядку тем
    rows = []
    part1_points = part1_max = 0
    part2_points = part2_max = 0

    for link in se.exam_exercises.select_related('exercise__section').order_by('order_idx'):
        ex = link.exercise
        sec = ex.section
        sub = subs_map.get(ex.id)

        # для test: 1 балл за верный, max=1
        if ex.exercise_type == 'test':
            earned = sub.grade if (sub and sub.grade is not None) else 0
            maxp = 1
            part1_points += earned
            part1_max += maxp

        # для open: берем sub.grade, а max = section.max_score
        else:
            earned = sub.grade if (sub and sub.grade is not None) else 0
            maxp = sec.max_score
            part2_points += earned
            part2_max += maxp

        rows.append({
            'idx': link.order_idx,
            'earned': earned,
            'maxp': maxp,
        })

    total_primary = part1_points + part2_points
    total_max = part1_max + part2_max

    SCALE = {
        1: 6, 2: 11, 3: 17, 4: 22, 5: 27,
        6: 34, 7: 40, 8: 46, 9: 52, 10: 58,
        11: 64, 12: 70, 13: 72, 14: 74, 15: 76,
        16: 78, 17: 80, 18: 82, 19: 84, 20: 86,
        21: 88, 22: 90, 23: 92, 24: 94, 25: 95,
        26: 96, 27: 97, 28: 98, 29: 99, 30: 100,
        31: 100, 32: 100
    }

    # итоговый тестовый балл по шкале (0 оставляем 0)
    test_score = SCALE.get(total_primary, 0)

    return render(request, 'exams/results.html', {
        'exam': se,
        'part1_points': part1_points,
        'part1_max': part1_max,
        'part2_points': part2_points,
        'part2_max': part2_max,
        'total_primary': total_primary,
        'total_max': total_max,
        'test_score': test_score,
        'scaled': SCALE,
        'rows': rows,
    })


@login_required
def finish_exam(request, exam_id):
    """
    Завершить экзамен: пометить completed_at и вернуть на список.
    """
    if request.method in ('POST', 'GET'):
        se = get_object_or_404(StudentExam, pk=exam_id, student=request.user)
        se.completed_at = timezone.now()
        se.save()
    return redirect('exams:list')


