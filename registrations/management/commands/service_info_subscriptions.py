from os import environ
import logging

from django.core.management.base import BaseCommand, CommandError
from registrations.models import SubscriptionRequest

from ndoh_hub.utils import sbm_client


class Command(BaseCommand):
    log = logging.getLogger("registrations")
    help = ('Subscribes all current WhatsApp subscription users to the '
            'correct place in the service info messageset')

    def add_arguments(self, parser):
        parser.add_argument(
            '--sbm-url', dest='sbm_url',
            default=environ.get('STAGE_BASED_MESSAGING_URL'),
            help=('The Stage Based Messaging Service for '
                  'service info subscriptions'))
        parser.add_argument(
            '--sbm-token', dest='sbm_token',
            default=environ.get('STAGE_BASED_MESSAGING_TOKEN'),
            help=('The Authorization token for the SBM Service')
        )

    def handle(self, *args, **kwargs):
        sbm_url = kwargs['sbm_url']
        sbm_token = kwargs['sbm_token']

        if not sbm_url:
            raise CommandError(
                'Please make sure either the STAGE_BASED_MESSAGING_URL '
                'environment variable or --sbm-url is set.')

        if not sbm_token:
            raise CommandError(
                'Please make sure either the STAGE_BASED_MESSAGING_TOKEN '
                'environment variable or --sbm-token is set.')

        messageset_mapping = {
            ms['id']: ms['short_name']
            for ms in sbm_client.get_messagesets()["results"]
        }

        service_info_messageset = next(sbm_client.get_messagesets(
            {"short_name": "whatsapp_service_info.hw_full.1"})["results"])

        subscriptions = sbm_client.get_subscriptions({
            "messageset_contains": "whatsapp_momconnect_",
            "active": True,
        })["results"]

        for subscription in subscriptions:
            messageset = messageset_mapping[subscription["messageset"]]
            if "hw_full" not in messageset:
                # We only want to subscribe full clinic subscriptions
                continue

            if self.identity_has_service_info_subscription(
                    messageset_mapping, subscription["identity"]):
                # They already have an active service info subscription, skip
                self.log.debug(
                    "%s already has a service info subscription, skipping",
                    subscription["identity"])
                continue

            sequence = self.service_info_sequence(
                messageset,
                subscription["next_sequence_number"]
            )
            self.log.debug(
                "Creating service info subscription request for %s",
                subscription["identity"])
            SubscriptionRequest.objects.create(
                identity=subscription["identity"],
                messageset=service_info_messageset["id"],
                next_sequence_number=sequence,
                lang=subscription["lang"],
                schedule=service_info_messageset["default_schedule"],
            )

    def service_info_sequence(self, short_name: str, sequence: int) -> int:
        """
        Calculates the sequence number that the service info messageset should
        be on, given the existing subscription that a user has
        """
        # TODO: work out the actual logic here
        # whatsapp_momconnect_prebirth.hw_partial.1
        # whatsapp_momconnect_postbirth.hw_full.1
        # whatsapp_momconnect_postbirth.hw_full.2
        # whatsapp_momconnect_prebirth.hw_full.1
        # whatsapp_momconnect_prebirth.hw_full.2
        # whatsapp_momconnect_prebirth.hw_full.3
        # whatsapp_momconnect_prebirth.hw_full.4
        # whatsapp_momconnect_prebirth.hw_full.5
        # whatsapp_momconnect_prebirth.hw_full.6
        # whatsapp_momconnect_prebirth.patient.1
        return 1

    def identity_has_service_info_subscription(
            self, messageset_mapping: dict, identity: str) -> bool:
        """
        Whether or not the given identity has an active subscription to the
        service info messageset.

        Args:
            messageset_mapping (dict):
                Mapping between messageset keys and names
            identity (str): The UUID of the identity
        """
        subscriptions = [
            messageset_mapping[sub["messageset"]] for sub in
            sbm_client.get_subscriptions({
                "active": True,
                "identity": identity,
            })["results"]
        ]
        return "whatsapp_service_info.hw_full.1" in subscriptions
