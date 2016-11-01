from . import models  # noqa
from django.db.models.signals import post_save, pre_save  # noqa
from django.dispatch import receiver


@receiver(post_save, sender=models.Registration)
def psh_validate_subscribe(sender, instance, created, **kwargs):
    """ Post save hook to fire Registration validation task
    """
    if created:
        from .tasks import validate_subscribe
        validate_subscribe.apply_async(
            kwargs={"registration_id": str(instance.id)})


@receiver(pre_save, sender=models.Registration)
def psh_push_registration_to_jembi(sender, instance, raw, **kwargs):
    """
    Pre-save hook to push registrations to Jembi, only schedule the push
    if the validated state flips from False to True.

    NOTE:   It is important that this is a pre-save hook because we want to
            track changes between a previous record version (non-existent
            or in the db) and what we're saving now to be able to track
            a `validated` state going from `False` to `True`
    """
    # raw is when data is loaded with existing data like fixtures
    if raw:
        return

    registrations = models.Registration.objects.all()

    if registrations.filter(pk=instance.pk).exists():
        # Fetch the registration as it is in the database so we can
        # compare the values we're about to save to the database
        db_registration = models.Registration.objects.get(pk=instance.pk)
        # If it wasn't validated before but is now then
        # we need to notify Jembi
        if not db_registration.validated and instance.validated:
            from .tasks import push_registration_to_jembi
            push_registration_to_jembi.apply_async(
                kwargs={"registration_id": str(instance.id)})
    elif instance.validated:
        # If it's new but validated then we also need to notify Jembi
        from .tasks import push_registration_to_jembi
        push_registration_to_jembi.apply_async(
            kwargs={"registration_id": str(instance.id)})
