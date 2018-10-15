from django.core.management.base import BaseCommand

from registrations.models import SubscriptionRequest
from ndoh_hub import utils


class Command(BaseCommand):
    help = "Move all active nurseconnect subscriptions to the RTHB messageset"

    def handle(self, *args, **options):
        r = utils.get_messageset_schedule_sequence("nurseconnect_rthb.hw_full.1", None)
        messageset_id, messageset_schedule, next_sequence_number = r
        r = utils.get_messageset_schedule_sequence(
            "whatsapp_nurseconnect_rthb.hw_full.1", None
        )
        wa_messageset_id, wa_messageset_schedule, wa_next_sequence_number = r

        subscriptions = utils.sbm_client.get_subscriptions(
            params={"active": True, "messageset_contains": "nurseconnect"}
        )["results"]

        for subscription in subscriptions:
            # Skip any existing RTHB subscriptions
            if (
                subscription["messageset"] == messageset_id
                and subscription["next_sequence_number"] == next_sequence_number
            ):
                continue
            if (
                subscription["messageset"] == wa_messageset_id
                and subscription["next_sequence_number"] == wa_next_sequence_number
            ):
                continue

            identity = subscription["identity"]
            self.stdout.write("Switching subscription for {}".format(identity))

            # Get the old messageset
            ms = utils.sbm_client.get_messageset(subscription["messageset"])
            # Deactivate the old subscription
            utils.sbm_client.update_subscription(
                subscription["id"], data={"active": False}
            )

            # Create the new subscription to the rthb messageset
            if "whatsapp" in ms["short_name"]:
                SubscriptionRequest.objects.create(
                    identity=identity,
                    messageset=wa_messageset_id,
                    next_sequence_number=wa_next_sequence_number,
                    lang=subscription["lang"],
                    schedule=wa_messageset_schedule,
                )
            else:
                SubscriptionRequest.objects.create(
                    identity=identity,
                    messageset=messageset_id,
                    next_sequence_number=next_sequence_number,
                    lang=subscription["lang"],
                    schedule=messageset_schedule,
                )
