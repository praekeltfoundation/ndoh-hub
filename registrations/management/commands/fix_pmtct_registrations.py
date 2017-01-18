from django.core.management.base import BaseCommand

from registrations.models import Registration
from registrations.tasks import validate_subscribe


class Command(BaseCommand):
    help = ("Find and fixes all PMTCT registrations that aren't validated"
            "because of the edd date not being populated")

    def handle(self, *args, **kwargs):

        registrations = Registration.objects.filter(
            validated=False,
            reg_type__in=("pmtct_prebirth", "pmtct_postbirth")).iterator()

        updates = 0

        for registration in registrations:

            related_regs = Registration.objects.filter(
                    validated=True,
                    registrant_id=registration.registrant_id
                ).exclude(reg_type__in=("pmtct_prebirth", "pmtct_postbirth")).\
                order_by('-created_at')

            for related_reg in related_regs:

                if related_reg.data.get("edd"):
                    del registration.data["invalid_fields"]
                    registration.data["edd"] = related_reg.data["edd"]
                    registration.save()

                    validate_subscribe.apply_async(
                        kwargs={"registration_id": str(registration.id)})

                    updates += 1
                    break

        self.log("%s registrations fixed and validated." % (updates))

    def log(self, log):
        self.stdout.write('%s\n' % (log,))
