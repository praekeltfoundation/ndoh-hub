from django.apps import AppConfig
from django.db.models.signals import post_save, pre_save  # noqa


class RegistrationsAppConfig(AppConfig):
    name = "registrations"
