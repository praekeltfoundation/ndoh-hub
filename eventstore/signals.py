from django.db.models.signals import post_save
from django.dispatch import receiver

from eventstore.models import OpenHIMQueue, PrebirthRegistration


@receiver(post_save, sender=PrebirthRegistration)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        OpenHIMQueue.objects.create(
            object_id=instance.id,
            object_type=OpenHIMQueue.ObjectType.PREBIRTH_REGISTRATION,
        )
