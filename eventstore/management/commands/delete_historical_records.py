import logging

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

VALID_MODELS = {"Event", "Message"}


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "model",
            type=str,
            help="Specify the model you want to delete the records for.(Event/Message)",
        )
        parser.add_argument(
            "retention_period",
            type=int,
            help="Specify the retention period in months",
            default=60
        )

    def handle(self, *args, **options):
        model_name = options["model"]
        retention_period = options["retention_period"]

        if model_name not in VALID_MODELS:
            raise Exception("Invalid model specified")

        model = apps.get_model("eventstore", model_name)

        filter_date = timezone.now() - relativedelta(months=retention_period, hour=0)
        count, _ = model.objects.filter(timestamp__lt=filter_date).delete()
        logger.info(f"Deleted {count} {model_name.lower()}(s)")
