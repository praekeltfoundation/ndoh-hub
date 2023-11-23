from django.apps import AppConfig


class EventstoreConfig(AppConfig):
    name = "eventstore"

    def ready(self):
        import eventstore.signals  # noqa
