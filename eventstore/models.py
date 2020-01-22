import uuid

from django.conf.locale import LANG_INFO
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone

LANGUAGE_TYPES = ((v["code"].rstrip("-za"), v["name"]) for v in LANG_INFO.values())

SAID_IDTYPE = "sa_id"
PASSPORT_IDTYPE = "passport"
DOB_IDTYPE = "dob"
IDTYPES = (
    (SAID_IDTYPE, "SA ID"),
    (PASSPORT_IDTYPE, "Passport"),
    (DOB_IDTYPE, "Date of birth"),
)
PASSPORT_COUNTRY_TYPES = (
    ("zw", "Zimbabwe"),
    ("mz", "Mozambique"),
    ("mw", "Malawi"),
    ("ng", "Nigeria"),
    ("cd", "DRC"),
    ("so", "Somalia"),
    ("other", "Other"),
)


class OptOut(models.Model):
    STOP_TYPE = "stop"
    FORGET_TYPE = "forget"
    LOSS_TYPE = "loss"
    OPTOUT_TYPES = ((STOP_TYPE, "Stop"), (FORGET_TYPE, "Forget"), (LOSS_TYPE, "Loss"))

    NOT_USEFUL_REASON = "not_useful"
    OTHER_REASON = "other"
    UNKNOWN_REASON = "unknown"
    SMS_FAILURE_REASON = "sms_failure"
    MISCARRIAGE_REASON = "miscarriage"
    STILLBIRTH_REASON = "stillbirth"
    BABYLOSS_REASON = "babyloss"
    NOT_HIV_POSITIVE_REASON = "not_hiv_pos"
    REASON_TYPES = (
        (NOT_USEFUL_REASON, "Not useful"),
        (OTHER_REASON, "Other"),
        (UNKNOWN_REASON, "Unknown"),
        (SMS_FAILURE_REASON, "SMS failure"),
        (MISCARRIAGE_REASON, "Miscarriage"),
        (STILLBIRTH_REASON, "Stillbirth"),
        (BABYLOSS_REASON, "Lost baby"),
        (NOT_HIV_POSITIVE_REASON, "Not HIV positive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    optout_type = models.CharField(max_length=6, choices=OPTOUT_TYPES)
    reason = models.CharField(max_length=11, choices=REASON_TYPES)
    source = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return "{} opt out: {} <{}>".format(
            self.get_optout_type_display(), self.get_reason_display(), self.contact_id
        )


class BabySwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Baby switches"


class ChannelSwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    from_channel = models.CharField(max_length=255)
    to_channel = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Channel switches"


class MSISDNSwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    old_msisdn = models.CharField(max_length=255)
    new_msisdn = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class LanguageSwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    old_language = models.CharField(max_length=255)
    new_language = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class IdentificationSwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    old_identification_type = models.CharField(max_length=8, choices=IDTYPES)
    new_identification_type = models.CharField(max_length=8, choices=IDTYPES)
    old_id_number = models.CharField(max_length=13, blank=True, default="")
    new_id_number = models.CharField(max_length=13, blank=True, default="")
    old_dob = models.DateField(blank=True, null=True, default=None)
    new_dob = models.DateField(blank=True, null=True, default=None)
    old_passport_country = models.CharField(
        choices=PASSPORT_COUNTRY_TYPES, max_length=5, blank=True, default=""
    )
    new_passport_country = models.CharField(
        choices=PASSPORT_COUNTRY_TYPES, max_length=5, blank=True, default=""
    )
    old_passport_number = models.CharField(max_length=255, blank=True, default="")
    new_passport_number = models.CharField(max_length=255, blank=True, default="")
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class ResearchOptinSwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    old_research_consent = models.BooleanField()
    new_research_consent = models.BooleanField()
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class PublicRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    device_contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    language = models.CharField(max_length=3, choices=LANGUAGE_TYPES)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class CHWRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    device_contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    id_type = models.CharField(max_length=8, choices=IDTYPES)
    id_number = models.CharField(max_length=13, blank=True)
    passport_country = models.CharField(
        max_length=5, blank=True, choices=PASSPORT_COUNTRY_TYPES
    )
    passport_number = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    language = models.CharField(max_length=3, choices=LANGUAGE_TYPES)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class PrebirthRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    device_contact_id = models.UUIDField()
    id_type = models.CharField(max_length=8, choices=IDTYPES)
    id_number = models.CharField(max_length=13, blank=True)
    passport_country = models.CharField(
        max_length=5, blank=True, choices=PASSPORT_COUNTRY_TYPES
    )
    passport_number = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    language = models.CharField(max_length=3, choices=LANGUAGE_TYPES)
    edd = models.DateField()
    facility_code = models.CharField(max_length=6)
    source = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class PostbirthRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    device_contact_id = models.UUIDField()
    id_type = models.CharField(max_length=8, choices=IDTYPES)
    id_number = models.CharField(max_length=13, blank=True)
    passport_country = models.CharField(
        max_length=5, blank=True, choices=PASSPORT_COUNTRY_TYPES
    )
    passport_number = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    language = models.CharField(max_length=3, choices=LANGUAGE_TYPES)
    baby_dob = models.DateField()
    facility_code = models.CharField(max_length=6)
    source = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class Message(models.Model):
    INBOUND = "I"
    OUTBOUND = "O"
    DIRECTION_TYPES = [(INBOUND, "Inbound"), (OUTBOUND, "Outbound")]

    id = models.CharField(max_length=255, primary_key=True, blank=True)
    contact_id = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    type = models.CharField(max_length=255, blank=True)
    data = JSONField(default=dict, blank=True, null=True)
    message_direction = models.CharField(max_length=1, choices=DIRECTION_TYPES)
    created_by = models.CharField(max_length=255, blank=True)
    fallback_channel = models.BooleanField(default=False)

    @property
    def is_operator_message(self):
        """
        Whether this message is from an operator on the frontend
        """
        try:
            return (
                self.message_direction == self.OUTBOUND
                and self.type == "text"
                and self.data["_vnd"]["v1"]["author"]["type"] == "OPERATOR"
                and bool(self.data["_vnd"]["v1"]["chat"]["owner"])
            )
        except (KeyError, TypeError):
            return False


class Event(models.Model):
    message_id = models.CharField(max_length=255, blank=True)
    recipient_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True)
    data = JSONField(default=dict, blank=True, null=True)
    fallback_channel = models.BooleanField(default=False)


class ExternalRegistrationID(models.Model):
    """
    Keeps track of all the registration IDs that we've processed from external
    registrations, so that we can deduplicate on them
    """

    id = models.CharField(max_length=255, primary_key=True)
