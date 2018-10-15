from os import environ

from django.core.management.base import BaseCommand, CommandError

from registrations.models import Registration
from registrations.tasks import add_personally_identifiable_fields, validate_subscribe

from seed_services_client import StageBasedMessagingApiClient

from ._utils import validate_and_return_url


class Command(BaseCommand):
    help = (
        "Validates all invalid Registrations that failed with the given "
        "error. This should also lead to the creation of a  Subscription "
        "in the SBM service"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--sbm-url",
            dest="sbm_url",
            type=validate_and_return_url,
            default=environ.get("STAGE_BASED_MESSAGING_URL"),
            help=("The Stage Based Messaging Service to verify " "subscriptions for."),
        )
        parser.add_argument(
            "--sbm-token",
            dest="sbm_token",
            default=environ.get("STAGE_BASED_MESSAGING_TOKEN"),
            help=("The Authorization token for the SBM Service"),
        )
        parser.add_argument(
            "--invalid-field",
            dest="invalid_field",
            default=None,
            help=(
                "Field that failed to validate when registration was "
                "created. Must match 'invalid_field' in registration data"
            ),
        )
        parser.add_argument(
            "--batch-size",
            dest="batch_size",
            type=int,
            default=None,
            help=(
                "The number of registrations to process. This allows batch "
                "processing."
            ),
        )

    def handle(self, *args, **kwargs):
        sbm_url = kwargs["sbm_url"]
        sbm_token = kwargs["sbm_token"]
        invalid_field = kwargs["invalid_field"]
        batch_size = kwargs["batch_size"]

        if not sbm_url:
            raise CommandError(
                "Please make sure either the STAGE_BASED_MESSAGING_URL "
                "environment variable or --sbm-url is set."
            )

        if not sbm_token:
            raise CommandError(
                "Please make sure either the STAGE_BASED_MESSAGING_TOKEN "
                "environment variable or --sbm-token is set."
            )
        client = StageBasedMessagingApiClient(sbm_token, sbm_url)

        registrations = Registration.objects.filter(
            validated=False, data__invalid_fields__contains=[invalid_field]
        )

        if batch_size is not None:
            registrations = registrations[:batch_size]

        count = 0
        for reg in registrations.iterator():
            self.log("Validating registration %s" % reg.id)
            if self.count_subscriptions(client, reg):
                self.log(
                    ("Identity %s already has subscription. Skipping.")
                    % (reg.registrant_id)
                )
                continue

            # validate_subscribe() checks all data for the registration is
            # valid and creates the Subscription Request
            if not reg.data.get("msisdn_device", ""):
                add_personally_identifiable_fields(reg)
            reg.save()
            result = validate_subscribe(registration_id=str(reg.id))
            if not result:
                reg.refresh_from_db()
                "Registration %s still invalid" % reg.id
            else:
                count += 1
        self.log("Successfully revalidated %s registrations" % count)

    def log(self, log):
        self.stdout.write("%s\n" % (log,))

    def count_subscriptions(self, sbm_client, registration):
        subscriptions = sbm_client.get_subscriptions(
            {"identity": registration.registrant_id, "active": True}
        )
        count = len(list(subscriptions["results"]))
        return count
