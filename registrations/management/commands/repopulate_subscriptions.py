from os import environ

from django.core.management.base import BaseCommand, CommandError

from registrations.models import Registration
from registrations.tasks import add_personally_identifiable_fields, validate_subscribe

from seed_services_client import StageBasedMessagingApiClient

from ._utils import validate_and_return_url


class Command(BaseCommand):
    help = (
        "Validates all Registrations without Subscription Requests and "
        "creates one for each. This should also lead to the creation of a "
        "Subscription in the SMB service"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--blind",
            action="store_false",
            default=True,
            dest="check_subscription",
            help=(
                "Do not check with the stage based messaging API whether"
                "or not a subscription for the identity already exists."
                "NOT RECOMMENDED AT ALL"
            ),
        )
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
            "--reg-query",
            dest="query",
            default=None,
            help=("Filter query to restrict registrations searched"),
        )
        parser.add_argument(
            "--start-date",
            dest="start_date",
            default=None,
            help=(
                "Filter query to restrict registrations searched to "
                "only those newer than given datetime"
            ),
        )

    def handle(self, *args, **kwargs):
        sbm_url = kwargs["sbm_url"]
        sbm_token = kwargs["sbm_token"]
        check_subscription = kwargs["check_subscription"]
        query = kwargs["query"]
        start_date = kwargs["start_date"]

        if check_subscription:
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

        filters = {"validated": True}
        if query:
            try:
                query_key, query_value = query.split(":", 1)
            except ValueError:
                raise CommandError(
                    "Please use the format 'key':'value' for --reg-query"
                )
            filters[query_key] = query_value
        if start_date:
            filters["created_at__gte"] = start_date
        registrations = Registration.objects.filter(**filters)

        for reg in registrations:
            requests = reg.get_subscription_requests()
            if requests.exists():
                continue
            if check_subscription and self.count_subscriptions(client, reg):
                self.log(
                    (
                        "Registration %s without Subscription Requests "
                        "already has subscription (identity: %s). "
                        "Skipping."
                    )
                    % (reg.pk, reg.registrant_id)
                )
                continue

            """
            validate_subscribe() ensures no invalid registrations get
            subscriptions and creates the Subscription Request
            """
            add_personally_identifiable_fields(reg)
            reg.save()
            validate_subscribe.apply_async(kwargs={"registration_id": str(reg.id)})
            self.log(
                "Attempted to repopulate subscriptions for registration "
                "%s" % (reg.id)
            )

    def log(self, log):
        self.stdout.write("%s\n" % (log,))

    def count_subscriptions(self, sbm_client, registration):
        subscriptions = sbm_client.get_subscriptions(
            {"identity": registration.registrant_id}
        )
        count = len(list(subscriptions["results"]))
        return count
