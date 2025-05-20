from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class PracticeConfig(AppConfig):
    name = 'practice'

    def ready(self):
        # это сообщение должно появиться в логах при старте сервера
        logger.debug("[PracticeConfig] ready() called, importing signals…")
        import practice.signals  # noqa
