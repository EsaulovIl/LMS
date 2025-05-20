# submissions/management/commands/fill_submissionfiles.py
from django.core.management.base import BaseCommand
from submissions.models import SubmissionFile

class Command(BaseCommand):
    help = "Обновить content_url у всех SubmissionFile через Yandex.Disk API"

    def handle(self, *args, **options):
        qs = SubmissionFile.objects.exclude(disk_path__isnull=True).exclude(disk_path__exact='')
        total = qs.count()
        self.stdout.write(f"Будет обновлено {total} ссылок...")
        for idx, sf in enumerate(qs, start=1):
            sf.save(update_fields=['content_url'])
            self.stdout.write(f"[{idx}/{total}] #{sf.pk}: {sf.file_path} → {sf.content_url}")
        self.stdout.write(self.style.SUCCESS("Готово."))
