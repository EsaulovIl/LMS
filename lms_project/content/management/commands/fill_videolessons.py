from django.core.management.base import BaseCommand
from content.models import VideoLesson

class Command(BaseCommand):
    help = "Fill content_url for all existing Notebooks via Yandex.Disk API"

    def handle(self, *args, **options):
        for vd in VideoLesson.objects.all():
            vd.save(update_fields=["video_url"])
            self.stdout.write(f"{vd.id}: {vd.title} → {vd.video_url}")
