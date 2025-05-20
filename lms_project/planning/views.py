# apps/planning/views.py
from datetime import date, timedelta, timezone
import random
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static
from django.urls import reverse
from collections import Counter, defaultdict

from .models import ThemeSchedule, PlanEntry, Plan
from daily.models import DailyQuizTask, DailyQuizAssignment
from practice.models import PracticeAssignment, PracticeAssignmentExercise
from homework.models import Homework, HomeworkExercise
from submissions.models import Submission, Exercise
from courses.models import Section
from content.models import Theme, VideoLesson, Notebook, VideoProgress

from exams.models import StudentExam


@login_required
def home_view(request):
    if request.user.role.name != 'student':
        return redirect('mentors:home')
    # today = date.today()
    today = date(2025, 5, 19)
    # 1) Пытаемся получить уже созданное назначение на сегодня
    assignment = DailyQuizAssignment.objects.filter(
        user=request.user,
        assigned_date=today
    ).first()

    # 2) Если нет — выбираем случайное задание, которое пользователь ещё не делал
    if not assignment:
        done_ids = DailyQuizAssignment.objects.filter(
            user=request.user
        ).values_list('task_id', flat=True)
        candidates = DailyQuizTask.objects.exclude(id__in=done_ids)
        if candidates.exists():
            task = random.choice(list(candidates))
            assignment = DailyQuizAssignment.objects.create(
                user=request.user,
                task_id=task.id,
                assigned_date=today
            )
        else:
            assignment = None

    notes = request.user.notifications.all()[:5]
    unread_count = request.user.notifications.filter(read_at__isnull=True).count()

    # блок «Текущая тема»
    current_entry = (
        ThemeSchedule.objects
        .filter(plan__student=request.user, scheduled_date__lte=today)
        .select_related('theme', 'section')
        .order_by('-scheduled_date')
        .first()
    )

    if current_entry:
        videos = VideoLesson.objects.filter(theme=current_entry.theme)
        notebooks = Notebook.objects.filter(theme=current_entry.theme)
        # Подгрузка домашки для текущей темы (если она создана)
        current_homework = Homework.objects.filter(
            schedule=current_entry
        ).select_related('schedule').first()
    else:
        videos = VideoLesson.objects.none()
        notebooks = Notebook.objects.none()
        current_homework = None

    # Подгрузка домашки для текущей темы (если она создана)
    current_homework = None
    if current_entry:
        current_homework = Homework.objects.filter(
            schedule=current_entry
        ).select_related('schedule').first()

    homework = Homework.objects.filter(schedule=current_entry).first() if current_entry else None
    hw_status = None

    if homework:
        # через HomeworkExercise
        hw_exs = HomeworkExercise.objects.filter(homework=homework).select_related('exercise')
        # тестовые
        test_qs = hw_exs.filter(exercise__exercise_type='test')
        test_total = test_qs.count()
        test_done = test_qs.filter(status=HomeworkExercise.AUTO_GRADED).count()
        # открытые
        open_qs = hw_exs.exclude(exercise__exercise_type='test')
        open_total = open_qs.count()
        # сколько открытых отправлено (есть сабмит)
        submitted_open = Submission.objects.filter(
            student=request.user,
            exercise__in=open_qs.values_list('exercise', flat=True)
        ).values('exercise').distinct().count()
        # сколько открытых проверено
        open_graded = open_qs.filter(status=HomeworkExercise.GRADED).count()

        # определяем статус
        if test_done == test_total and open_graded == open_total:
            hw_status = 'выполнено'
        elif submitted_open == open_total and open_total > 0:
            hw_status = 'на проверке'
        elif (test_done + submitted_open) > 0:
            hw_status = 'в процессе'
        else:
            hw_status = 'не начато'

    # блок «Отработки»
    practice_assignments = (
        PracticeAssignment.objects
        .filter(student=request.user)
        .filter(
            ex_links__status=PracticeAssignmentExercise.PENDING
        )
        .select_related('theme__section')
        .prefetch_related('ex_links')
        .order_by('deadline')
        .distinct()
    )

    return render(request, 'planning/home.html', {
        'today_date': today,
        'notifications': notes,
        'unread_count': unread_count,
        'assignment': assignment,
        'current_entry': current_entry,
        'notebooks': notebooks,
        'current_homework': current_homework,
        'practice_assignments': practice_assignments,
        'hw_status': hw_status,
    })


@login_required
def calendar_view(request):
    # 1) Сколько «шагов» n недель от today: по GET-параметру ?week_start=YYYY-MM-DD
    week_start_str = request.GET.get('week_start')
    if week_start_str:
        try:
            start = date.fromisoformat(week_start_str)
        except ValueError:
            start = date.today()
    else:
        start = date.today()

    # Отматываем до понедельника
    start = start - timedelta(days=start.weekday())
    end = start + timedelta(days=6)

    # Пресеты для ← и → навигации
    prev_week = start - timedelta(weeks=1)
    next_week = start + timedelta(weeks=1)

    # 2) Собираем события из трёх источников
    events = []

    # — теория (ThemeSchedule)
    qs1 = ThemeSchedule.objects.filter(
        plan__student=request.user,
        scheduled_date__range=(start, end)
    ).select_related('theme')
    for sched in qs1:
        # пытаемся найти домашку на эту тему
        hw = Homework.objects.filter(schedule=sched).first()
        events.append({
            'date': sched.scheduled_date,
            'type': 'теория',
            'title': sched.theme.name,
            'deadline': hw.deadline if hw else None,
            'url': reverse('planning:theme_content',
                           args=[sched.section_id, sched.theme_id]),
            'icon_url': static('image/theory.png'),
        })

    # — домашки
    qs2 = Homework.objects.filter(
        schedule__plan__student=request.user,
        assigned_at__date__range=(start, end)
    ).select_related('schedule__theme')
    for hw in qs2:
        events.append({
            'date': hw.assigned_at.date(),
            'type': 'домашка',
            'title': f"Домашка: {hw.schedule.theme.name}",
            'deadline': hw.deadline,
            'url': reverse('homework:detail', args=[hw.pk]),
            'icon_url': static('image/exercise.png'),
        })

    # Практика — ставим на день assigned_at, дедлайн в заголовке
    qs3 = PracticeAssignment.objects.filter(
        student=request.user,
        assigned_at__date__range=(start, end)
    ).select_related('theme')
    for pa in qs3:
        events.append({
            'date': pa.assigned_at.date(),
            'type': 'отработка',
            'title': f"Отработка: {pa.theme.name}",
            'deadline': pa.deadline,
            'url': reverse('practice:topic_exercises',
                           args=[pa.theme.section_id, pa.theme_id]),
            'icon_url': static('image/exercise.png'),
        })

        # — пробники (StudentExam)
    qs4 = StudentExam.objects.filter(
        student=request.user,
        assigned_at__date__range=(start, end)
    ).select_related('variant')
    for se in qs4:
        events.append({
            'date': se.assigned_at.date(),
            'type': 'пробник',
            'title': f"Пробник: {se.variant.name}",
            'deadline': se.deadline,
            'url': reverse('exams:detail', args=[se.pk]),
            'icon_url': static('image/exercise.png'),
        })

    # 3) Группируем события по дате
    events_by_day = defaultdict(list)
    for ev in events:
        events_by_day[ev['date']].append(ev)

    # 4) Собираем явный список дней с уже вложенными событиями
    week_days = [start + timedelta(days=i) for i in range(7)]
    days = [
        {
            'date': d,
            'events': events_by_day.get(d, []),
        }
        for d in week_days
    ]

    # 5) Отдаём в шаблон
    return render(request, 'planning/calendar.html', {
        'start': start,
        'end': end,
        'prev_week': prev_week,
        'next_week': next_week,
        'days': days,
    })


@login_required
def course_view(request):
    # 1) Найдём план текущего пользователя или 404
    plan = get_object_or_404(Plan, student=request.user)

    # 2) Через related_name 'entries' получим все PlanEntry, уже с section
    entries = (
        plan.entries
        .select_related('section')
        .order_by('order_idx')
    )

    # 3) Для каждого entry считаем статистику
    for entry in entries:
        section = entry.section

        # – теория: видео
        total_videos = VideoLesson.objects.filter(theme__section=section).count()
        done_videos = VideoProgress.objects.filter(
            student=request.user,
            video__theme__section=section,
            viewed=True
        ).count()

        entry.theory_total = total_videos
        entry.theory_done = done_videos

        # — практика: домашние задания
        hw_qs = Homework.objects.filter(
            schedule__plan=plan,
            schedule__section=section
        )
        entry.practice_total = hw_qs.count()
        # считаем, сколько из них полностью выполнено
        entry.practice_done = sum(
            1 for hw in hw_qs
            if hw.get_status() == 'выполнено'
        )

    # 4) Передаём сегодня́шнюю дату, чтобы вывести рядом в заголовке
    today_date = date(2025, 5, 8)

    return render(request, 'planning/course.html', {
        'entries': entries,
        'today_date': today_date,
    })


@login_required
def course_block_themes(request, section_id):
    plan = get_object_or_404(Plan, student=request.user)
    section = get_object_or_404(Section, pk=section_id)

    # 1) берём все расписания тем
    sched_qs = (
        ThemeSchedule.objects
        .filter(plan=plan, section=section)
        .select_related('theme')
        .order_by('scheduled_date')
    )

    # 2) пересчитываем статус
    for sched in sched_qs:
        sched.recalculate_status()

    # 3) плейсхолдер для темы
    placeholder = static('image/course-placeholder.png')

    themes = []
    total = sched_qs.count()

    for idx, sched in enumerate(sched_qs):
        theme = sched.theme

        # теория
        theory_total = VideoLesson.objects.filter(theme=theme).count()
        theory_done = VideoProgress.objects.filter(
            student=request.user,
            video__theme=theme,
            viewed=True
        ).count()

        # практика (домашки)
        hw_qs = Homework.objects.filter(schedule__plan=plan, schedule__theme=theme)
        practice_total = hw_qs.count()
        practice_done = sum(1 for hw in hw_qs if hw.get_status() == 'выполнено')

        themes.append({
            'id': theme.id,
            'name': theme.name,
            'image_url': getattr(theme, 'image_url', placeholder),
            'theory_total': theory_total,
            'theory_done': theory_done,
            'practice_total': practice_total,
            'practice_done': practice_done,
            'status': sched.status,
            'status_display': sched.get_status_display(),
            'is_final': (idx == total - 1),
            'scheduled_date': sched.scheduled_date,
            'url': reverse('planning:theme_content', args=[section_id, theme.id]),
        })

    today_date = date(2025, 5, 8)

    return render(request, 'planning/course_block_themes.html', {
        'section': section,
        'themes': themes,
        'today_date': today_date,
    })


@login_required
def theme_content(request, section_id, theme_id):
    """
    Показывает видео, тетрадки и ссылку на домашку по теме.
    """
    plan = get_object_or_404(Plan, student=request.user)
    section = get_object_or_404(Section, pk=section_id)
    theme = get_object_or_404(Theme, pk=theme_id, section=section)

    # найдём расписание этой темы
    sched = get_object_or_404(
        ThemeSchedule,
        plan=plan,
        section=section,
        theme=theme
    )

    # контент по теме
    videos = VideoLesson.objects.filter(theme=theme)
    notebooks = Notebook.objects.filter(theme=theme)

    # домашка, если создана
    homework = Homework.objects.filter(schedule=sched).first()
    hw_status = homework.get_status() if homework else None

    # прогресс пользователя по просмотру видео
    prog_qs = VideoProgress.objects.filter(
        student=request.user,
        video__in=videos
    )
    # собираем словарь video_id → VideoProgress
    progress_map = {vp.video_id: vp for vp in prog_qs}

    return render(request, 'planning/theme_content.html', {
        'section': section,
        'theme': theme,
        'videos': videos,
        'notebooks': notebooks,
        'homework': homework,
        'progress_map': progress_map,
        'hw_status': hw_status,
    })
