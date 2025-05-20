import logging
import random
from typing import List
from django.db.models import Max
from submissions.models import Submission, Exercise
from homework.models import Homework, HomeworkExercise

logger = logging.getLogger(__name__)

def generate_remediation_for_homework(homework_id: int) -> List[Exercise]:
    logger.debug(f"[remediation] start for homework_id={homework_id}")

    # 0) Получаем домашку и студента
    try:
        hw = Homework.objects.select_related('schedule__plan__student').get(pk=homework_id)
    except Homework.DoesNotExist:
        logger.warning(f"[remediation] Homework {homework_id} not found")
        return []
    student = hw.schedule.plan.student

    # 1) Упражнения домашки
    hw_ex_ids = list(
        HomeworkExercise.objects
        .filter(homework=hw)
        .values_list('exercise_id', flat=True)
    )
    logger.debug(f"[remediation] hw_ex_ids={hw_ex_ids}")
    if not hw_ex_ids:
        return []

    # 2) Последние сабмиты
    last_subs_q = (
        Submission.objects
        .filter(
            student=student,
            exercise_id__in=hw_ex_ids,
            status__in=['auto-graded', 'graded']
        )
        .values('exercise_id')
        .annotate(last_pk=Max('pk'))
    )
    last_pks = [row['last_pk'] for row in last_subs_q]
    logger.debug(f"[remediation] last submission PKs={last_pks}")
    last_subs = Submission.objects.select_related('exercise__section', 'exercise__similarity_group')\
                                  .filter(pk__in=last_pks)

    # 3) «Провальные» по баллам
    failed_ex_ids = []
    for sub in last_subs:
        sec_max = sub.exercise.section.max_score or 0
        sc = sub.score or 0
        logger.debug(f"[remediation] sub_id={sub.pk} ex_id={sub.exercise_id} score={sc} sec_max={sec_max}")
        if sc < sec_max:
            failed_ex_ids.append(sub.exercise_id)
    logger.debug(f"[remediation] failed_ex_ids={failed_ex_ids}")
    if not failed_ex_ids:
        return []

    remediation = []
    for ex_id in failed_ex_ids:
        ex = Exercise.objects.select_related('similarity_group', 'theme').get(pk=ex_id)
        logger.debug(f"[remediation] processing failed ex {ex_id} (sim_group={ex.similarity_group_id})")

        # пытаемся взять одно аналогичное
        if ex.similarity_group_id:
            candidates = Exercise.objects.filter(
                similarity_group=ex.similarity_group
            ).exclude(id__in=hw_ex_ids + remediation)
            logger.debug(f"[remediation] analog candidates for ex {ex_id}: {[c.id for c in candidates]}")
        else:
            candidates = Exercise.objects.filter(
                theme=ex.theme
            ).exclude(id__in=hw_ex_ids + remediation)
            logger.debug(f"[remediation] theme candidates for ex {ex_id}: {[c.id for c in candidates]}")

        if candidates:
            choice = random.choice(list(candidates))
            remediation.append(choice.id)
            logger.debug(f"[remediation] picked ex {choice.id} for failed {ex_id}")
        else:
            logger.debug(f"[remediation] no candidates found for ex {ex_id}")

    logger.debug(f"[remediation] final remediation list: {remediation}")
    # возвращаем реальные объекты
    return list(Exercise.objects.filter(id__in=remediation))
