from django.db.models.signals import post_save
from django.dispatch import receiver

from eventstore.models import (
    ChannelSwitch,
    CHWRegistration,
    OpenHIMQueue,
    OptOut,
    PrebirthRegistration,
    PublicRegistration,
)


@receiver(post_save, sender=PrebirthRegistration)
def queue_prebirth_registration(sender, instance, created, **kwargs):
    if created:
        OpenHIMQueue.objects.create(
            object_id=instance.id,
            object_type=OpenHIMQueue.ObjectType.PREBIRTH_REGISTRATION,
        )


@receiver(post_save, sender=PublicRegistration)
def queue_public_registration(sender, instance, created, **kwargs):
    if created:
        OpenHIMQueue.objects.create(
            object_id=instance.id,
            object_type=OpenHIMQueue.ObjectType.PUBLIC_REGISTRATION,
        )


@receiver(post_save, sender=CHWRegistration)
def queue_chw_registration(sender, instance, created, **kwargs):
    if created:
        OpenHIMQueue.objects.create(
            object_id=instance.id,
            object_type=OpenHIMQueue.ObjectType.CHW_REGISTRATION,
        )


@receiver(post_save, sender=ChannelSwitch)
def queue_channel_switch(sender, instance, created, **kwargs):
    if created:
        OpenHIMQueue.objects.create(
            object_id=instance.id,
            object_type=OpenHIMQueue.ObjectType.CHANNEL_SWITCH,
        )


@receiver(post_save, sender=OptOut)
def queue_optout(sender, instance, created, **kwargs):
    if created:
        OpenHIMQueue.objects.create(
            object_id=instance.id,
            object_type=OpenHIMQueue.ObjectType.OPTOUT,
        )
