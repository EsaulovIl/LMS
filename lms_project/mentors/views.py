from datetime import timedelta
from functools import wraps
import logging

from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.db.models import Q

from submissions.models import Submission, SubmissionFile, SubmissionFeedback
from submissions.forms import SubmissionFileForm
from homework.models import Homework
from exams.models import StudentExam, StudentExamExercise, ExamSubmissionFeedback, ExamSubmission

from submissions.utils import upload_file_to_yadisk, get_student_mentor

from utils.yadisk import get_yadisk_download_link

from homework.models import HomeworkExercise
from practice.models import PracticeAssignmentExercise, PracticeAssignment

logger = logging.getLogger(__name__)


def mentor_required(view_func):
    """
    Decorator: пропускает только залогиненных менторов,
    иначе редиректит на логин или даёт 403.
    """

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if request.user.role.name != 'mentor':
            return HttpResponseForbidden("Доступ только для менторов")
        return view_func(request, *args, **kwargs)

    return _wrapped


@login_required
@mentor_required
def mentor_check_list(request):
    mentor = request.user
    # 1) все студенты вашего ментора
    student_ids = mentor.mentored_groups.values_list('students__pk', flat=True)

    # === Домашки ===
    base_hw = (
        Homework.objects
        .filter(
            schedule__plan__student__in=student_ids,
            exercises__exercise_type='open',
            exercises__submissions__student__in=student_ids
        )
        .distinct()
        .select_related('schedule__plan__student', 'schedule__theme')
        .order_by('-assigned_at')
    )

    pending_hw = (
        base_hw
        .filter(exercises__submissions__status='pending')
        .filter(
            Q(exercises__submissions__grader=mentor) |
            Q(exercises__submissions__grader__isnull=True)
        )
        .distinct()
    )

    reviewed_hw = base_hw.exclude(pk__in=pending_hw.values_list('pk', flat=True))

    # === Отработки ===
    base_pr = (
        PracticeAssignment.objects
        .filter(
            student__in=student_ids,
            ex_links__exercise__exercise_type='open',
            ex_links__exercise__submissions__student__in=student_ids
        )
        .distinct()
        .select_related('student', 'theme')
        .order_by('-assigned_at')
    )

    pending_pr = (
        base_pr
        .filter(ex_links__status=PracticeAssignmentExercise.PENDING)
        .filter(
            Q(ex_links__exercise__submissions__grader=mentor) |
            Q(ex_links__exercise__submissions__grader__isnull=True)
        )
        .distinct()
    )

    reviewed_pr = base_pr.exclude(pk__in=pending_pr.values_list('pk', flat=True))

    # Собираем единый список pending и reviewed
    pending = []
    for hw in pending_hw:
        # первая «открытая» домашка без проверки
        ex = hw.exercises.through.objects.filter(
            homework=hw,
            status=HomeworkExercise.PENDING,
            exercise__exercise_type='open'
        ).select_related('exercise').first().exercise
        pending.append({
            'kind': 'homework',
            'pk': hw.pk,
            'student': hw.schedule.plan.student,
            'theme': hw.schedule.theme,
            'assigned_at': hw.assigned_at,
            'deadline': hw.deadline,
            'ex_pk': ex.pk,
        })
    for pa in pending_pr:
        ex = pa.ex_links.filter(
            status=PracticeAssignmentExercise.PENDING,
            exercise__exercise_type='open'
        ).select_related('exercise').first().exercise
        pending.append({
            'kind': 'practice',
            'pk': pa.pk,
            'student': pa.student,
            'theme': pa.theme,
            'assigned_at': pa.assigned_at,
            'deadline': pa.deadline,
            'ex_pk': ex.pk,
        })

    reviewed = []
    for hw in reviewed_hw:
        ex = hw.exercises.through.objects.filter(
            homework=hw,
            status=HomeworkExercise.GRADED,
            exercise__exercise_type='open'
        ).select_related('exercise').first().exercise
        reviewed.append({
            'kind': 'homework',
            'pk': hw.pk,
            'student': hw.schedule.plan.student,
            'theme': hw.schedule.theme,
            'assigned_at': hw.assigned_at,
            'deadline': hw.deadline,
            'ex_pk': ex.pk,
        })
    for pa in reviewed_pr:
        ex = pa.ex_links.filter(
            status=PracticeAssignmentExercise.GRADED,
            exercise__exercise_type='open'
        ).select_related('exercise').first().exercise
        reviewed.append({
            'kind': 'practice',
            'pk': pa.pk,
            'student': pa.student,
            'theme': pa.theme,
            'assigned_at': pa.assigned_at,
            'deadline': pa.deadline,
            'ex_pk': ex.pk,
        })

    # пагинация pending
    paginator = Paginator(pending, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'mentors/check_list.html', {
        'pending': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'reviewed': reviewed,
    })


@login_required
@mentor_required
def mentor_homework_detail(request, homework_pk, exercise_pk):
    mentor = request.user

    # 1) Пытаемся найти HomeworkExercise
    hw_ex = (
        HomeworkExercise.objects
        .filter(
            homework_id=homework_pk,
            exercise_id=exercise_pk
        )
        .select_related('homework__schedule__plan__student', 'exercise')
        .first()
    )

    if hw_ex:
        assignment_type = 'homework'
        assignment = hw_ex.homework
        student = assignment.schedule.plan.student
        ex_links = list(assignment.ex_link.select_related('exercise'))
    else:
        # 2) Иначе — PracticeAssignmentExercise
        pa_ex = (
            PracticeAssignmentExercise.objects
            .filter(
                assignment_id=homework_pk,
                exercise_id=exercise_pk
            )
            .select_related('assignment__student', 'exercise')
            .first()
        )
        if not pa_ex:
            return HttpResponseBadRequest("Неверное упражнение для этой проверки.")
        assignment_type = 'practice'
        assignment = pa_ex.assignment
        student = assignment.student
        ex_links = list(assignment.ex_links.select_related('exercise'))
    # 3) Проверяем, что именно вы — куратор этого студента
    if not mentor.mentored_groups.filter(students=student).exists():
        return HttpResponseBadRequest("У вас нет доступа к проверке этого задания.")

    # 4) Навигация по упражнениям
    ex_ids = [link.exercise.pk for link in ex_links]
    if exercise_pk not in ex_ids:
        # если вдруг не попадает — перенаправляем на первый
        return redirect('mentors:check_detail', assignment_pk=homework_pk, exercise_pk=ex_ids[0])

    idx = ex_ids.index(exercise_pk)
    prev_id = ex_ids[idx - 1] if idx > 0 else None
    next_id = ex_ids[idx + 1] if idx < len(ex_ids) - 1 else None
    current_index = idx  # 0-based


    # 4) Обработка POST — сохраняем только для этого упражнения
    if request.method == 'POST':
        link = ex_links[idx]
        ex = link.exercise

        sub = (
            Submission.objects
            .filter(student=student, exercise=ex, status='pending')
            .order_by('-submitted_at')
            .first()
        )
        if sub:
            # назначаем проверяющего
            if sub.grader is None:
                sub.grader = mentor

            # сохраняем оценку
            grade_val = request.POST.get(f'grade_{ex.pk}')
            if grade_val:
                try:
                    sub.score = int(grade_val)
                except ValueError:
                    pass

            sub.status = 'graded'
            sub.save(update_fields=['grader', 'score', 'status'])

            # отзыв
            fb, created = SubmissionFeedback.objects.get_or_create(
                submission=sub,
                mentor=mentor,
                defaults={
                    'feedback': request.POST.get(f'feedback_{ex.pk}', '').strip(),
                    'grade': sub.score or 0,
                }
            )
            if not created:
                fb.feedback = request.POST.get(f'feedback_{ex.pk}', '').strip()
                fb.grade = sub.score or 0

            # файл ментора
            file_field = request.FILES.get(f'solution_{ex.pk}')
            if file_field:
                try:
                    disk_path, content_url = upload_file_to_yadisk(
                        file_field,
                        student_id=student.id,
                        assignment_type='homework',
                        assignment_id=assignment.pk,
                        exercise_id=ex.pk,
                        mentor=True,
                        mentor_id=mentor.id
                    )
                    fb.file_path = file_field.name
                    fb.disk_path = disk_path
                    fb.content_url = content_url
                except Exception as e:
                    logger.error("YDisk upload error: %s", e, exc_info=True)
                    fb.file_path = file_field.name

            fb.save(update_fields=[
                'feedback', 'grade',
                'file_path', 'disk_path', 'content_url'
            ])

        return redirect('mentors:check_detail', homework_pk=assignment.pk, exercise_pk=exercise_pk)

    # 5) GET — готовим данные только для одного упражнения
    link = ex_links[idx]
    ex = link.exercise
    sub = (
        Submission.objects
        .filter(student=student, exercise=ex)
        .order_by('-submitted_at')
        .first()
    )
    fb = sub.feedbacks.filter(mentor=mentor).first() if sub else None

    max_score = link.exercise.section.max_score

    # 6) Ссылка на критерии (только для развёрнутых заданий)
    criteria_url = None
    if ex.exercise_type == 'open':
        # в имени файла используем номер задания — здесь просто order in list +1
        num = link.exercise.section.pk  # или link.order_idx, если номер задачи в ЕГЭ
        disk_path = f"/LMS/Критерии/{num}.png"
        try:
            criteria_url = get_yadisk_download_link(disk_path)
        except Exception:
            criteria_url = None

    context = {
        'homework': assignment,
        'student': student,
        'exercise': ex,
        'submission': sub,
        'student_files': sub.files.all() if sub else [],
        'max_score': max_score,
        'existing_feedback': fb,
        'ex_ids': ex_ids,
        'current_id': exercise_pk,
        'prev_id': prev_id,
        'next_id': next_id,
        'current_index': current_index,
        'criteria_url': criteria_url,
    }
    return render(request, 'mentors/homework_detail.html', context)


# apps/mentors/views.py
@login_required
@mentor_required
def mentor_exams_list(request):
    mentor = request.user
    # 1) Все ученики ментора
    student_ids = mentor.mentored_groups.values_list('students__pk', flat=True)

    # 2) Их завершённые экзамены
    exams_qs = (
        StudentExam.objects
        .filter(student__id__in=student_ids, completed_at__isnull=False)
        .select_related('student', 'variant')
        .order_by('-completed_at')
    )

    # 3) Из каждого экзамена берём только тот, где есть непроставленные open-задания
    pending = []
    for exam in exams_qs:
        # all StudentExamExercise для части open
        open_links = exam.exam_exercises.filter(
            exercise__exercise_type='open'
        ).order_by('order_idx')

        if not open_links.exists():
            continue

        # те, по которым ещё нет фидбэка от _этого_ ментора
        reviewed = set(
            ExamSubmissionFeedback.objects
            .filter(exam_exercise__in=open_links, mentor=mentor)
            .values_list('exam_exercise_id', flat=True)
        )

        # если есть хоть одна открытая задача без фидбэка — добавляем экзамен
        if any(link.pk not in reviewed for link in open_links):
            # сохраняем PK первого неревьювнутого упражнения
            first_pending = next(link.pk for link in open_links if link.pk not in reviewed)
            pending.append({
                'exam': exam,
                'first_exercise_link_pk': first_pending
            })

    # 4) Пагинация
    paginator = Paginator(pending, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'mentors/exams_list.html', {
        'exams': page_obj.object_list,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
    })


@login_required
@mentor_required
def mentor_exam_review(request, exam_pk):
    # 1) Загружаем экзамен и его open-упражнения
    exam = get_object_or_404(StudentExam, pk=exam_pk)
    links = list(
        exam.exam_exercises
        .filter(exercise__exercise_type='open')
        .select_related('exercise__section')
        .order_by('order_idx')
    )
    if not links:
        return HttpResponseBadRequest("Нет открытых заданий для проверки")

    # 2) Определяем студента и ментора
    student = exam.student
    mentor = request.user

    # 3) Навигация по order_idx
    indices = [ln.order_idx for ln in links]
    try:
        idx = int(request.GET.get('q', indices[0]))
    except (TypeError, ValueError):
        idx = indices[0]
    if idx not in indices:
        idx = indices[0]

    link = next(ln for ln in links if ln.order_idx == idx)
    exercise = link.exercise

    # 4) Получаем последний pending- сабмит или создаём новый
    sub, created = ExamSubmission.objects.get_or_create(
        exam=exam,
        exercise=exercise,
        defaults={'status': 'pending', 'grader': mentor}
    )
    # Если сабмит уже был, но без ментора — назначаем
    if not created and sub.grader is None:
        sub.grader = mentor
        sub.save(update_fields=['grader'])

    student_files = sub.files.all()

    # 5) Существующий feedback от этого ментора
    fb = ExamSubmissionFeedback.objects.filter(
        exam_exercise=link, mentor=mentor
    ).first()

    file_form = SubmissionFileForm()

    # 6) POST — сохраняем файл, оценку и комментарий
    if request.method == 'POST':
        file_form = SubmissionFileForm(request.POST, request.FILES)

        # получаем числовую оценку
        grade_val = request.POST.get('grade') or 0
        try:
            grade = int(grade_val)
        except ValueError:
            grade = 0
        sub.grade = grade
        sub.status = 'graded'
        sub.save(update_fields=['grade', 'status'])

        comment = request.POST.get('feedback', '').strip()

        if fb is None:
            fb = ExamSubmissionFeedback(
                exam_exercise=link,
                mentor=mentor,
                grade=grade,
                feedback=comment
            )
        else:
            fb.grade = grade
            fb.feedback = comment

        # файл ментора
        if file_form.is_valid():
            mf = file_form.cleaned_data['file']
            disk_path, content_url = upload_file_to_yadisk(
                mf,
                student_id=student.id,
                assignment_type='exam',
                assignment_id=exam.pk,
                exercise_id=exercise.pk,
                mentor=True,
                mentor_id=mentor.id
            )
            fb.file_path = mf.name
            fb.disk_path = disk_path
            fb.content_url = content_url

        fb.save()

        # перенаправляем обратно на тот же ?q=
        return redirect(f"{request.path}?q={idx}")

    # 7) GET — отрисовываем страницу
    max_score = exercise.section.max_score

    # 6) Ссылка на критерии (только для развёрнутых заданий)
    criteria_url = None
    if exercise.exercise_type == 'open':
        # в имени файла используем номер задания — здесь просто order in list +1
        num = link.order_idx  # или link.order_idx, если номер задачи в ЕГЭ
        disk_path = f"/LMS/Критерии/{num}.png"
        try:
            criteria_url = get_yadisk_download_link(disk_path)
        except Exception:
            criteria_url = None

    return render(request, 'mentors/exam_review.html', {
        'exam': exam,
        'links': links,
        'indices': indices,
        'idx': idx,
        'link': link,
        'exercise': exercise,
        'student_files': student_files,
        'existing_fb': fb,
        'max_score': max_score,
        'file_form': file_form,
        'criteria_url': criteria_url,
    })
