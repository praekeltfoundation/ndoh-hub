from django.apps import AppConfig

from django.db.models.signals import post_save


class ChangesAppConfig(AppConfig):

    name = 'changes'

    def ready(self):
        from .signals import psh_validate_implement

        post_save.connect(
            psh_validate_implement,
            sender='changes.Change')
