# submissions/management/commands/fill_feedback_links.py

from django.core.management.base import BaseCommand
from submissions.models import SubmissionFeedback
from utils.yadisk import get_yadisk_download_link

class Command(BaseCommand):
    help = (
        "Обновить прямые ссылки (content_url) у всех SubmissionFeedback "
        "по их disk_path через Yandex.Disk API"
    )

    def handle(self, *args, **options):
        qs = SubmissionFeedback.objects.exclude(disk_path__isnull=True).exclude(disk_path__exact='')
        total = qs.count()
        if not total:
            self.stdout.write("Нет SubmissionFeedback с заполненным disk_path.")
            return

        self.stdout.write(f"Будет обновлено {total} ссылок в SubmissionFeedback...")
        for idx, fb in enumerate(qs, start=1):
            try:
                href = get_yadisk_download_link(fb.disk_path)
                fb.content_url = href
                fb.save(update_fields=['content_url'])
                self.stdout.write(f"[{idx}/{total}] #{fb.pk}: {fb.disk_path} → {href}")
            except Exception as e:
                self.stderr.write(
                    f"[{idx}/{total}] Ошибка для #{fb.pk} ({fb.disk_path}): {e}"
                )
        self.stdout.write(self.style.SUCCESS("Готово."))
