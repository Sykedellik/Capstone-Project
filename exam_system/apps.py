from django.apps import AppConfig


class ExamSystemConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'exam_system'

    def ready(self):
        import exam_system.signals
