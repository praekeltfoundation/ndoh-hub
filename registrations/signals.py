# from .models import Registration


def psh_validate_subscribe(sender, instance, created, **kwargs):
    """ Post save hook to fire Registration validation task
    """
    if created:
        from .tasks import validate_subscribe

        validate_subscribe.apply_async(kwargs={"registration_id": str(instance.id)})


def psh_fire_created_metric(sender, instance, created, **kwargs):
    """ Post save hook to fire Registration created metric
    """
    if created:
        from ndoh_hub import utils

        utils.fire_metric.apply_async(
            kwargs={"metric_name": "registrations.created.sum", "metric_value": 1.0}
        )
