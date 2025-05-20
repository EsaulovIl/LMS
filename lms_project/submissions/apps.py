from django.apps import AppConfig

class SubmissionsConfig(AppConfig):
    name = 'submissions'

    def ready(self):
        # импортим модуль с сигналами, чтобы они подключились
        import submissions.signals
