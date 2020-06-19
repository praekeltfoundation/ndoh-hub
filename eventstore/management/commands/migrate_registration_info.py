from django.core.management.base import BaseCommand

from eventstore.models import (
    CHWRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
)
from ndoh_hub.utils import rapidpro


class Command(BaseCommand):
    help = (
        "Migrates the preferred channel data from all registrations that don't "
        "have a channel, sends a request to RapidPro to look up the channel "
        "for the contact, and adds it to the registration"
    )

    def handle_channel_migration(self):
        for each in PublicRegistration.objects.filter(channel=""):
            contact = rapidpro.get_contacts(uuid=each.contact_id).first()
            if contact.fields["preferred_channel"] != "":
                each.channel = contact.fields["preferred_channel"]
                each.save(update_fields=["channel"])

        for each in PrebirthRegistration.objects.filter(channel=""):
            contact = rapidpro.get_contacts(uuid=each.contact_id).first()
            if contact.fields["preferred_channel"] != "":
                each.channel = contact.fields["preferred_channel"]
                each.save(update_fields=["channel"])

        for each in PostbirthRegistration.objects.filter(channel=""):
            contact = rapidpro.get_contacts(uuid=each.contact_id).first()
            if contact.fields["preferred_channel"] != "":
                each.channel = contact.fields["preferred_channel"]
                each.save(update_fields=["channel"])

        for each in CHWRegistration.objects.filter(channel=""):
            contact = rapidpro.get_contacts(uuid=each.contact_id).first()
            if contact.fields["preferred_channel"] != "":
                each.channel = contact.fields["preferred_channel"]
                each.save(update_fields=["channel"])

    def handle(self, *args, **options):
        self.handle_channel_migration()
