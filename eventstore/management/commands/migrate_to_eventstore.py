import time

from django.core.management.base import BaseCommand

from eventstore.models import (
    CHWRegistration,
    PMTCTRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
)
from ndoh_hub.constants import LANGUAGES
from registrations.models import Registration


class Command(BaseCommand):
    help = (
        "Migrates all the data from the registrations and changes apps into the "
        "eventstore"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete",
            "-d",
            action="store_true",
            help="Deletes the migrated registrations and changes",
        )

    def execute_with_progress(self, func, iterator):
        total = 0
        start, d_print = time.time(), time.time()
        for arg in iterator:
            func(arg)
            if time.time() - d_print > 1:
                self.stdout.write(
                    f"\rProcessed {total} at {total/(time.time() - start):.0f}/s",
                    ending="",
                )
                d_print = time.time()
            total += 1
        self.stdout.write("")

    def handle_public_registration(self, reg):
        data = reg.data or {}
        if "whatsapp" in reg.reg_type:
            channel = "WhatsApp"
        else:
            channel = "SMS"
        uuid_registrant = data.pop("uuid_registrant", None)
        operator_id = data.pop("operator_id", None)
        uuid_device = data.pop("uuid_device", None)
        language = data.pop("language", "")
        if language in LANGUAGES:
            language = language.rstrip("_ZA")
        else:
            language = ""

        PublicRegistration.objects.update_or_create(
            id=reg.id,
            defaults={
                "contact_id": reg.registrant_id or uuid_registrant,
                "device_contact_id": operator_id or uuid_device,
                "source": reg.source.name,
                "language": language,
                "channel": channel,
                "timestamp": reg.created_at,
                "created_by": reg.source.user.username,
                "data": data,
            },
        )

    def handle_CHW_registration(self, reg):
        data = reg.data or {}
        if "whatsapp" in reg.reg_type:
            channel = "WhatsApp"
        else:
            channel = "SMS"
        uuid_registrant = data.pop("uuid_registrant", None)
        operator_id = data.pop("operator_id", None)
        uuid_device = data.pop("uuid_device", None)
        id_type = data.pop("id_type", "")
        id_number = data.pop("sa_id_no", "")
        passport_country = data.pop("passport_origin", "")
        passport_number = data.pop("passport_no", "")
        date_of_birth = data.pop("mom_dob", None)
        language = data.pop("language", "")
        if language in LANGUAGES:
            language = language.rstrip("_ZA")
        else:
            language = ""

        CHWRegistration.objects.update_or_create(
            id=reg.id,
            defaults={
                "contact_id": reg.registrant_id or uuid_registrant,
                "device_contact_id": operator_id or uuid_device,
                "source": reg.source.name,
                "id_type": {"none": "dob"}.get(id_type, id_type),
                "id_number": id_number,
                "passport_country": passport_country,
                "passport_number": passport_number,
                "date_of_birth": date_of_birth,
                "channel": channel,
                "language": language,
                "timestamp": reg.created_at,
                "created_by": reg.source.user.username,
                "data": data,
            },
        )

    def handle_prebirth_registration(self, reg):
        data = reg.data or {}
        if "whatsapp" in reg.reg_type:
            channel = "WhatsApp"
        else:
            channel = "SMS"
        uuid_registrant = data.pop("uuid_registrant", None)
        contact_id = reg.registrant_id or uuid_registrant
        uuid_device = data.pop("uuid_device", None)
        operator_id = data.pop("operator_id", None)
        id_type = data.pop("id_type", "")
        id_number = data.pop("sa_id_no", "")
        passport_country = data.pop("passport_origin", "")
        passport_number = data.pop("passport_no", "")
        date_of_birth = data.pop("mom_dob", None)
        facility_code = data.pop("faccode", "")
        edd = data.pop("edd", None)
        language = data.pop("language", "")
        if language in LANGUAGES:
            language = language.rstrip("_ZA")
        else:
            language = ""

        PrebirthRegistration.objects.update_or_create(
            id=reg.id,
            defaults={
                "contact_id": contact_id,
                "device_contact_id": operator_id or uuid_device or contact_id,
                "id_type": {"none": "dob"}.get(id_type, id_type),
                "id_number": id_number,
                "passport_country": passport_country,
                "passport_number": passport_number,
                "date_of_birth": date_of_birth,
                "channel": channel,
                "language": language,
                "edd": edd,
                "facility_code": facility_code,
                "source": reg.source.name,
                "timestamp": reg.created_at,
                "created_by": reg.source.user.username,
                "data": data,
            },
        )

    def handle_PMTCT_registration(self, reg):
        data = reg.data or {}
        operator_id = data.pop("operator_id", None)
        date_of_birth = data.pop("mom_dob", None)

        PMTCTRegistration.objects.update_or_create(
            id=reg.id,
            defaults={
                "contact_id": reg.registrant_id,
                "device_contact_id": operator_id or reg.registrant_id,
                "source": reg.source.name,
                "date_of_birth": date_of_birth,
                "timestamp": reg.created_at,
                "created_by": reg.source.user.username,
                "data": data,
            },
        )

    def handle(self, *args, **options):
        queries = {
            "public": Registration.objects.filter(
                reg_type__in=("momconnect_prebirth", "whatsapp_prebirth"),
                source__authority="patient",
                validated=True,
            ).select_related("source", "source__user"),
            "CHW": Registration.objects.filter(
                reg_type__in=("momconnect_prebirth", "whatsapp_prebirth"),
                source__authority="hw_partial",
                validated=True,
            ).select_related("source", "source__user"),
            "prebirth": Registration.objects.filter(
                reg_type__in=("momconnect_prebirth", "whatsapp_prebirth"),
                source__authority="hw_full",
                validated=True,
            ).select_related("source", "source__user"),
            "PMTCT": Registration.objects.filter(
                reg_type__in=(
                    "pmtct_prebirth",
                    "whatsapp_pmtct_prebirth",
                    "pmtct_postbirth",
                    "whatsapp_pmtct_postbirth",
                ),
                validated=True,
            ).select_related("source", "source__user"),
        }

        for name, query in queries.items():
            self.stdout.write(f"Processing {name} registrations...")
            self.execute_with_progress(
                getattr(self, f"handle_{name}_registration"), query.iterator()
            )
            if options["delete"]:
                self.stdout.write(f"Deleting {name} registrations...")
                query.delete()
