# from .models import Registration


def psh_validate_subscribe(sender, instance, created, **kwargs):
    """ Post save hook to fire Registration validation task
    """
    if created:
        from .tasks import validate_subscribe
        validate_subscribe.apply_async(
            kwargs={"registration_id": str(instance.id)})
