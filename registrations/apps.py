from django.apps import AppConfig

from django.db.models.signals import post_save, pre_save  # noqa


class RegistrationsAppConfig(AppConfig):

    name = 'registrations'

    def ready(self):
        from .signals import (
            psh_validate_subscribe, psh_push_registration_to_jembi)

        post_save.connect(
            psh_validate_subscribe,
            sender='registrations.Registration')
        pre_save.connect(
            psh_push_registration_to_jembi,
            sender='registrations.Registration')
