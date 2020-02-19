import time

from django.core.management.base import BaseCommand

from changes.models import Change
from eventstore.models import (
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
    IdentificationSwitch,
    LanguageSwitch,
    MSISDNSwitch,
    OptOut,
    PMTCTRegistration,
    PrebirthRegistration,
    PublicRegistration,
    EddSwitch,
    BabyDobSwitch,
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

    def handle_babyswitch_change(self, change):
        BabySwitch.objects.update_or_create(
            id=change.id,
            defaults={
                "contact_id": change.registrant_id,
                "source": change.source.name,
                "timestamp": change.created_at,
                "created_by": change.source.user.username,
                "data": change.data or {},
            },
        )

    def handle_optout_change(self, change):
        data = change.data or {}
        if change.action in ("pmtct_loss_switch", "momconnect_loss_switch"):
            optout_type = "loss"
        elif (
            change.data.get("identity_store_optout", {}).get("optout_type") == "forget"
        ):
            optout_type = "forget"
        else:
            optout_type = "stop"
        reason = data.pop("reason", "")

        OptOut.objects.update_or_create(
            id=change.id,
            defaults={
                "contact_id": change.registrant_id,
                "optout_type": optout_type,
                "reason": reason,
                "source": change.source.name,
                "timestamp": change.created_at,
                "created_by": change.source.user.username,
                "data": data,
            },
        )

    def handle_channelswitch_change(self, change):
        data = change.data or {}
        to_channel = {"sms": "SMS", "whatsapp": "WhatsApp"}[data.pop("channel")]
        from_channel = data.pop(
            "old_channel", {"SMS": "whatsapp", "WhatsApp": "sms"}[to_channel]
        )
        from_channel = {"sms": "SMS", "whatsapp": "WhatsApp"}[from_channel]
        ChannelSwitch.objects.update_or_create(
            id=change.id,
            defaults={
                "contact_id": change.registrant_id,
                "source": change.source.name,
                "from_channel": from_channel,
                "to_channel": to_channel,
                "timestamp": change.created_at,
                "created_by": change.source.user.username,
                "data": data,
            },
        )

    def handle_msisdnswitch_change(self, change):
        data = change.data or {}
        msisdn = data.pop("msisdn", "")
        MSISDNSwitch.objects.update_or_create(
            id=change.id,
            defaults={
                "contact_id": change.registrant_id,
                "source": change.source.name,
                "new_msisdn": msisdn,
                "timestamp": change.created_at,
                "created_by": change.source.user.username,
                "data": data,
            },
        )

    def handle_languageswitch_change(self, change):
        data = change.data or {}
        new_language = data.pop("language").rstrip("_ZA")
        old_language = (data.pop("old_language") or "").rstrip("_ZA")
        LanguageSwitch.objects.update_or_create(
            id=change.id,
            defaults={
                "contact_id": change.registrant_id,
                "source": change.source.name,
                "old_language": old_language,
                "new_language": new_language,
                "timestamp": change.created_at,
                "created_by": change.source.user.username,
                "data": data,
            },
        )

    def handle_eddswitch_change(self, change):
        data = change.data or {}
        new_edd = data.pop("edd")
        old_edd = (data.pop("old_edd") or "")
        EddSwitch.objects.update_or_create(
            id=change.id,
            defaults={
                "contact_id": change.registrant_id,
                "source": change.source.name,
                "old_edd": old_edd,
                "new_edd": new_edd,
                "timestamp": change.created_at,
                "created_by": change.source.user.username,
                "data": data,
            },
        )

    def handle_babydobswitch_change(self, change):
        data = change.data or {}
        new_baby_dob = data.pop("baby_dob")
        old_baby_dob = (data.pop("old_baby_dob") or "")
        BabyDobSwitch.objects.update_or_create(
            id=change.id,
            defaults={
                "contact_id": change.registrant_id,
                "source": change.source.name,
                "old_baby_dob": old_baby_dob,
                "new_baby_dob": new_baby_dob,
                "timestamp": change.created_at,
                "created_by": change.source.user.username,
                "data": data,
            },
        )

    def handle_identificationswitch_change(self, change):
        data = change.data or {}
        id_type = data.pop("id_type", "")
        passport_no = data.pop("passport_no", "")
        passport_origin = data.pop("passport_origin", "")
        sa_id_no = data.pop("sa_id_no", "")
        IdentificationSwitch.objects.update_or_create(
            id=change.id,
            defaults={
                "contact_id": change.registrant_id,
                "source": change.source.name,
                "new_identification_type": id_type,
                "new_passport_number": passport_no,
                "new_passport_country": passport_origin,
                "new_id_number": sa_id_no,
                "timestamp": change.created_at,
                "created_by": change.source.user.username,
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

        queries = {
            "babyswitch": Change.objects.filter(
                action="baby_switch", validated=True
            ).select_related("source", "source__user"),
            "optout": Change.objects.filter(
                action__in=(
                    "pmtct_loss_switch",
                    "pmtct_loss_optout",
                    "pmtct_nonloss_optout",
                    "momconnect_loss_switch",
                    "momconnect_loss_optout",
                    "momconnect_nonloss_optout",
                ),
                validated=True,
            ).select_related("source", "source__user"),
            "channelswitch": Change.objects.filter(
                action="switch_channel", validated=True
            ).select_related("source", "source__user"),
            "msisdnswitch": Change.objects.filter(
                action="momconnect_change_msisdn", validated=True
            ).select_related("source", "source__user"),
            "languageswitch": Change.objects.filter(
                action="momconnect_change_language", validated=True
            ).select_related("source", "source__user"),
            "identificationswitch": Change.objects.filter(
                action="momconnect_change_identification", validated=True
            ).select_related("source", "source__user"),
        }

        for name, query in queries.items():
            self.stdout.write(f"Processing {name} changes...")
            self.execute_with_progress(
                getattr(self, f"handle_{name}_change"), query.iterator()
            )
            if options["delete"]:
                self.stdout.write(f"Deleting {name} changes...")
                query.delete()
