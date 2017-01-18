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

            updated = False
            for related_reg in related_regs:
                for field in ['edd', 'language', 'mom_dob', 'operator_id']:

                    if (related_reg.data.get(field) and
                            not registration.data.get(field)):
                        registration.data[field] = related_reg.data[field]
                        updated = True

            if updated:
                registration.data.pop("invalid_fields", None)
                registration.save()

                validate_subscribe.apply_async(
                    kwargs={"registration_id": str(registration.id)})

                updates += 1

        self.log("%s registrations fixed and validated." % (updates))

    def log(self, log):
        self.stdout.write('%s\n' % (log,))
