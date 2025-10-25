from django.apps import AppConfig


class ArticlesConfig(AppConfig):
    """
    Import Article signals.
    """
    default_auto_field = "django.db.models.BigAutoField"
    name = "articles"

    def ready(self):
        import articles.signals
