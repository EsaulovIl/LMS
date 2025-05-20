import logging
from datetime import date, timedelta
from django.db.models.signals import post_save
from django.dispatch import receiver

from submissions.models import Submission
from practice.services.remediation_service import generate_remediation_for_homework
from practice.models import PracticeAssignment, PracticeAssignmentExercise
from homework.models import HomeworkExercise

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Submission)
def create_remediation_assignment(sender, instance: Submission, created, **kwargs):
    logger.debug(f"[signal] Submission saved: pk={instance.pk}, status={instance.status}")

    # 1) Интересуют только авто- или ручная проверка
    if instance.status not in ('auto-graded', 'graded'):
        logger.debug("[signal] skip: status not graded")
        return

    # 2) Если студент набрал полный балл по разделу — пропускаем
    sec_max = instance.exercise.section.max_score or 0
    sc = instance.score or 0
    logger.debug(f"[signal] score={sc}, section_max={sec_max}")
    if sc >= sec_max:
        logger.debug("[signal] skip: score >= section_max")
        return

    # 3) Находим родительскую домашку
    try:
        hw_ex = HomeworkExercise.objects.get(
            exercise=instance.exercise,
            homework__schedule__plan__student=instance.student
        )
        homework_id = hw_ex.homework_id
        logger.debug(f"[signal] found HomeworkExercise: pk={hw_ex.pk}, homework_id={homework_id}")
    except HomeworkExercise.DoesNotExist:
        logger.warning(f"[signal] no HomeworkExercise for ex={instance.exercise_id}, student={instance.student_id}")
        return

    # 4) Генерим отработку
    remediation_exs = generate_remediation_for_homework(homework_id)
    logger.debug(f"[signal] remediation_exs count={len(remediation_exs)}")

    if not remediation_exs:
        logger.debug("[signal] no remediation tasks generated")
        return

    # 5) Создаём/дополняем PracticeAssignment
    student = instance.student
    deadline = date.today() + timedelta(days=3)
    for ex in remediation_exs:
        pa, pa_created = PracticeAssignment.objects.get_or_create(
            student=student,
            theme=ex.theme,
            defaults={'deadline': deadline}
        )
        if pa_created:
            logger.debug(f"[signal] created new PracticeAssignment pk={pa.pk} for theme={ex.theme_id}")
        pae, pae_created = PracticeAssignmentExercise.objects.get_or_create(
            assignment=pa,
            exercise=ex,
        )
        logger.debug(f"[signal] PracticeAssignmentExercise for ex={ex.id} created? {pae_created}")

    logger.info(f"[signal] remediation assignment generated for homework {homework_id}")
