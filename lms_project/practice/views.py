from datetime import date

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from courses.models import Section
from content.models import Theme
from django.templatetags.static import static

from .models import PracticeAssignment, PracticeAssignmentExercise

from submissions.models import Submission
from django.db.models import Max


@login_required
def blocks_list(request):
    """
    Список разделов, в которых у текущего пользователя есть отработки,
    с подсчётом общего числа тем (practice_total) и числа полностью выполненных (practice_done).
    """
    today_date = date(2025, 5, 8)

    # 1) Берём все отработки студента, подтягиваем тему и раздел
    assignments = (
        PracticeAssignment.objects
        .filter(student=request.user)
        .select_related('theme__section')
        .prefetch_related('ex_links')  # ссылки на упражнения и их статусы
    )

    # 2) Собираем уникальные разделы
    sections = {pa.theme.section for pa in assignments}
    sections = sorted(sections, key=lambda s: s.id)

    # 3) Для каждого раздела вычисляем practice_total и practice_done
    for section in sections:
        # все отработки (по темам) в этом разделе
        pas = [pa for pa in assignments if pa.theme.section == section]
        section.practice_total = len(pas)

        done_count = 0
        for pa in pas:
            # сколько упражнений в этой отработке
            total_ex = pa.ex_links.count()
            # сколько из них уже отмечено авто-оценкой или ручной проверкой
            graded_ex = pa.ex_links.filter(
                status__in=[
                    PracticeAssignmentExercise.AUTO_GRADED,
                    PracticeAssignmentExercise.GRADED
                ]
            ).count()
            # считаем тему полностью сделанной, только если есть хоть одно упражнение
            # и все они уже проверены или авто-оценены
            if total_ex > 0 and graded_ex == total_ex:
                done_count += 1

        section.practice_done = done_count

    return render(request, 'practice/blocks_list.html', {
        'sections': sections,
        'today_date': today_date,
    })


@login_required
def block_topics(request, section_id):
    """
    Список тем для отработки в выбранном разделе.
    Для каждой темы считаем:
      - practice_total  — сколько упражнений назначено
      - practice_done   — сколько уже выполнено (auto-graded или graded)
      - status          — «не начато» / «в процессе» / «выполнено»
    """
    section = get_object_or_404(Section, pk=section_id)

    # Все отработки текущего студента в этом разделе
    assignments = (
        PracticeAssignment.objects
        .filter(student=request.user, theme__section=section)
        .select_related('theme')
        .prefetch_related('ex_links')
    )

    placeholder = static('image/course-placeholder.png')
    themes = []

    for pa in assignments:
        theme = pa.theme
        total = pa.ex_links.count()
        done = pa.ex_links.filter(
            status__in=[
                PracticeAssignmentExercise.AUTO_GRADED,
                PracticeAssignmentExercise.GRADED
            ]
        ).count()

        if total == 0:
            status = 'не начато'
        elif done == total:
            status = 'выполнено'
        else:
            status = 'в процессе'

        themes.append({
            'id': theme.id,
            'name': theme.name,
            'image_url': getattr(theme, 'image_url', placeholder),
            'practice_total': total,
            'practice_done': done,
            'status': status,
        })

    return render(request, 'practice/block_topics.html', {
        'section': section,
        'themes': themes,
    })


@login_required
def topic_exercises(request, section_id, theme_id):
    """
    Вместо списка упражнений — сразу редиректим на первое упражнение.
    """
    theme = get_object_or_404(Theme, pk=theme_id, section_id=section_id)
    assignment = get_object_or_404(
        PracticeAssignment,
        student=request.user,
        theme=theme
    )

    # собираем упорядоченный список ID упражнений
    ex_ids = list(
        assignment.ex_links
        .order_by('exercise_id')
        .values_list('exercise_id', flat=True)
    )
    if not ex_ids:
        # если упражнений нет — показываем пустую страницу
        return render(request, 'practice/topic_exercises.html', {
            'theme': theme,
            'assignment': assignment,
            'links': [],
        })

    # редирект на первое упражнение
    first_ex = ex_ids[0]
    return redirect('submissions:solve', assignment.pk, first_ex)
