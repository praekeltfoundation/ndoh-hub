from django.apps import AppConfig
from django.db.models.signals import post_save, pre_save  # noqa


class RegistrationsAppConfig(AppConfig):

    name = "registrations"

    def ready(self):
        from .signals import psh_validate_subscribe, psh_fire_created_metric

        post_save.connect(
            psh_validate_subscribe,
            sender="registrations.Registration",
            dispatch_uid="psh_validate_subscribe",
        )

        post_save.connect(
            psh_fire_created_metric,
            sender="registrations.Registration",
            dispatch_uid="psh_fire_created_metric",
        )
