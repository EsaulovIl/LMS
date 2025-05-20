from django.core.management.base import BaseCommand
from content.models import Notebook

class Command(BaseCommand):
    help = "Fill content_url for all existing Notebooks via Yandex.Disk API"

    def handle(self, *args, **options):
        for nb in Notebook.objects.all():
            nb.save(update_fields=["content_url"])
            self.stdout.write(f"{nb.id}: {nb.title} → {nb.content_url}")
