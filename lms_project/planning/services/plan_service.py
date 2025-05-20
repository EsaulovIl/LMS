# planning/services/plan_service.py

from datetime import date, timedelta, datetime, time
from django.db import transaction
from django.utils import timezone
from dateutil.relativedelta import relativedelta

from courses.models import Section
from content.models import Theme
from submissions.models import Exercise
from accounts.models import User
from onboarding.models import SurveyResponse, SurveyQuestion, TestResponse
from planning.models import Plan, PlanEntry, ThemeSchedule
from homework.models import Homework, HomeworkExercise

from exams.models import ExamVariant, StudentExam

# фиксированный «универсальный» порядок разделов
UNIVERSAL_SECTION_ORDER = [
    6, 7, 9, 4, 5, 10, 11, 2, 8, 12,
    1, 3, 13, 15, 16, 19, 17, 18, 14
]

# Веса разделов (для первичных баллов)
SECTION_WEIGHTS = {
    1: 1, 2: 1, 3: 1, 4: 1,
    5: 1, 6: 1, 7: 1, 8: 1,
    9: 1, 10: 1, 11: 1, 12: 1,
    13: 2, 14: 3, 15: 2, 16: 2,
    17: 3, 18: 4, 19: 4
}

# Шкала первичный → тестовый балл
PRIMARY_TO_TEST = {
    1: 6, 2: 11, 3: 17, 4: 22, 5: 27,
    6: 34, 7: 40, 8: 46, 9: 52, 10: 58,
    11: 64, 12: 70, 13: 72, 14: 74, 15: 76,
    16: 78, 17: 80, 18: 82, 19: 84, 20: 86,
    21: 88, 22: 90, 23: 92, 24: 94, 25: 95,
    26: 96, 27: 97, 28: 98, 29: 99, 30: 100,
    31: 100, 32: 100
}


def get_primary_score(desired_test_score: float) -> int:
    """Мин. первичный балл, при котором тестовый ≥ desired_test_score."""
    for p, t in sorted(PRIMARY_TO_TEST.items()):
        if t >= desired_test_score:
            return p
    return max(PRIMARY_TO_TEST)


@transaction.atomic
def generate_personal_plan(student_id: int) -> Plan:
    """
    1) Удаляем старый план
    2) Загружаем анкету и прогресс
    3) Отбираем и приоритизируем разделы
    4) Создаём Plan + PlanEntry
    5) Расписываем темы по дням, домашку – на тот же день
    6) Создаём пробники: назначаем на последний день каждого месяца
    """
    student = User.objects.get(pk=student_id)

    # 1) Стираем старый план
    Plan.objects.filter(student=student).delete()

    # 2) Анкета
    resp = SurveyResponse.objects.filter(user=student)
    target_q = SurveyQuestion.objects.get(name='target_score')
    weekly_q = SurveyQuestion.objects.get(name='weekly_hours')
    exam_q = SurveyQuestion.objects.get(name='exam_date')
    want_q = SurveyQuestion.objects.get(name='want_sections')
    know_q = SurveyQuestion.objects.get(name='know_sections')

    target_test = resp.get(question=target_q).value_number
    weekly_hours = float(resp.get(question=weekly_q).value_decimal or 0)

    ed = resp.filter(question=exam_q).first()
    if not ed or not ed.option:
        raise ValueError("Пожалуйста, выберите волну экзамена в анкете.")
    WAVE_DATES = {
        'early': date(2026, 3, 28),
        'main': date(2026, 5, 27),
        'reserve': date(2026, 6, 20),
    }
    exam_date = WAVE_DATES.get(ed.option.value)
    if not exam_date:
        raise ValueError(f"Неизвестная волна «{ed.option.value}».")

    want_secs = {int(r.option.value) for r in resp.filter(question=want_q)}
    know_secs = {int(r.option.value) for r in resp.filter(question=know_q)}

    # 2.1) Прогресс по входному тесту
    prog = {}
    for tr in TestResponse.objects.filter(user=student).select_related('question__section'):
        sid = tr.question.section_id
        rec = prog.setdefault(sid, {'total': 0, 'correct': 0})
        rec['total'] += 1
        rec['correct'] += int(tr.is_correct)
    progress_pct = {
        sid: (d['correct'] / d['total'] * 100 if d['total'] else 0)
        for sid, d in prog.items()
    }

    # 3) PRIMARY → TARGET → отбор разделов
    primary_goal = get_primary_score(target_test)
    selected, cum = [], 0
    for sid in UNIVERSAL_SECTION_ORDER:
        w = SECTION_WEIGHTS.get(sid, 1)
        if cum + w <= primary_goal:
            selected.append(sid)
            cum += w
        else:
            break

    # 3.1) Приоритизация: want∖know, want∩know, know∖want, low_progress, остальные
    low_prog = {sid for sid, pct in progress_pct.items() if pct < 70}
    prioritized = []

    for sid in selected:
        if sid in want_secs and sid not in know_secs:
            prioritized.append(sid)
    for sid in selected:
        if sid in want_secs and sid in know_secs and sid not in prioritized:
            prioritized.append(sid)
    for sid in selected:
        if sid in know_secs and sid not in prioritized:
            prioritized.append(sid)
    for sid in selected:
        if sid in low_prog and sid not in prioritized:
            prioritized.append(sid)
    for sid in selected:
        if sid not in prioritized:
            prioritized.append(sid)

    # 4) Создание Plan + PlanEntry
    plan = Plan.objects.create(student=student)
    per_section = max(1, primary_goal // len(prioritized))
    for idx, sid in enumerate(prioritized, start=1):
        PlanEntry.objects.create(
            plan=plan,
            section_id=sid,
            order_idx=idx,
            tasks_count=per_section
        )

    # 5) Расписание тем «плавно» по темпу ученика
    start_date = date.today()
    avg_topic_time = 3.0  # часов на тему
    topics_per_week = max(1, weekly_hours / avg_topic_time)
    interval_days = 7.0 / topics_per_week

    themes = []
    for sid in prioritized:
        themes += list(Theme.objects.filter(section_id=sid).order_by('id'))

    offset = 0.0
    for theme in themes:
        sched_date = start_date + timedelta(days=int(offset))
        ts = ThemeSchedule.objects.create(
            plan=plan,
            section=theme.section,
            theme=theme,
            scheduled_date=sched_date
        )

        # домашка в тот же день
        pe = plan.entries.get(section=theme.section)
        want_n = min(pe.tasks_count, 2)
        exs = list(Exercise.objects.filter(theme=theme))[:want_n]
        if exs:
            hw = Homework.objects.create(
                schedule=ts,
                assigned_at=timezone.make_aware(
                    datetime.combine(sched_date, time.min)
                ),
                deadline=sched_date + timedelta(days=3)
            )
            for ex in exs:
                HomeworkExercise.objects.create(homework=hw, exercise=ex)

        offset += interval_days

    # 6) Пробники — последний день каждого месяца до exam_date
    current = date.today().replace(day=1) + relativedelta(months=1)
    while current <= exam_date:
        last_day = (current + relativedelta(months=1)) - relativedelta(days=1)
        name = f"Пробник — {last_day.strftime('%B %Y')}"

        variant, _ = ExamVariant.objects.get_or_create(
            name=name,
            defaults={'deadline': last_day}
        )

        StudentExam.objects.update_or_create(
            variant=variant,
            student=student,
            defaults={
                'deadline': variant.deadline,
                # назначаем ровно на последний день месяца
                'assigned_at': timezone.make_aware(
                    datetime.combine(last_day, time.min)
                )
            }
        )

        current += relativedelta(months=1)

    return plan
