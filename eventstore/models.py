import uuid

import pycountry
from django.conf.locale import LANG_INFO
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone

from registrations.validators import geographic_coordinate, za_phone_number

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

SMS_CHANNELTYPE = "SMS"
WHATSAPP_CHANNELTYPE = "WhatsApp"
CHANNEL_TYPES = ((SMS_CHANNELTYPE, "SMS"), (WHATSAPP_CHANNELTYPE, "WhatsApp"))


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


class DeliveryFailure(models.Model):
    contact_id = models.CharField(primary_key=True, max_length=255, blank=False)
    number_of_failures = models.IntegerField(null=False, default=0)


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
    channel = models.CharField(max_length=8, choices=CHANNEL_TYPES, default="")
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
    channel = models.CharField(max_length=8, choices=CHANNEL_TYPES, default="")
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
    channel = models.CharField(max_length=8, choices=CHANNEL_TYPES, default="")
    edd = models.DateField()
    facility_code = models.CharField(max_length=6)
    source = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class PMTCTRegistration(models.Model):
    NORMAL = "normal"
    HIGH = "high"
    RISK_TYPES = ((NORMAL, "Normal"), (HIGH, "High"))
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    device_contact_id = models.UUIDField()
    date_of_birth = models.DateField(blank=True, null=True)
    pmtct_risk = models.CharField(choices=RISK_TYPES, max_length=6)
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
    channel = models.CharField(max_length=8, choices=CHANNEL_TYPES, default="")
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class EddSwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    old_edd = models.DateField()
    new_edd = models.DateField()
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class BabyDobSwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    old_baby_dob = models.DateField()
    new_baby_dob = models.DateField()
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

    def has_label(self, label):
        """
        Does this message have the specified label
        """
        if self.fallback_channel:
            return False

        labels = [
            l["value"]
            for l in self.data.get("_vnd", {}).get("v1", {}).get("labels", [])
        ]

        if label in labels:
            return True

        return False


class Event(models.Model):
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
    STATUS = [
        (SENT, "sent"),
        (DELIVERED, "delivered"),
        (READ, "read"),
        (FAILED, "failed"),
    ]

    message_id = models.CharField(max_length=255, blank=True)
    recipient_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=255, blank=True, choices=STATUS)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.CharField(max_length=255, blank=True)
    data = JSONField(default=dict, blank=True, null=True)
    fallback_channel = models.BooleanField(default=False)

    @property
    def is_hsm_error(self):
        """
        Is this a WhatsApp HSM error event
        """
        if self.fallback_channel:
            return False

        hsm_error = False
        for error in self.data.get("errors", []):
            if "structure unavailable" in error["title"]:
                hsm_error = True
            if "envelope mismatch" in error["title"]:
                hsm_error = True

        return hsm_error

    @property
    def is_message_expired_error(self):
        if self.fallback_channel:
            return False

        return any(error["code"] == 410 for error in self.data.get("errors", []))

    @property
    def is_whatsapp_failed_delivery_event(self):
        if self.fallback_channel:
            return False

        return self.status == "failed"


class ExternalRegistrationID(models.Model):
    """
    Keeps track of all the registration IDs that we've processed from external
    registrations, so that we can deduplicate on them
    """

    id = models.CharField(max_length=255, primary_key=True)


class Covid19Triage(models.Model):
    AGE_U18 = "<18"
    AGE_18T40 = "18-40"
    AGE_40T65 = "40-65"
    AGE_O65 = ">65"
    AGE_CHOICES = (
        (AGE_U18, AGE_U18),
        (AGE_18T40, AGE_18T40),
        (AGE_40T65, AGE_40T65),
        (AGE_O65, AGE_O65),
    )

    PROVINCE_CHOICES = sorted(
        (s.code, s.name) for s in pycountry.subdivisions.get(country_code="ZA")
    )

    EXPOSURE_YES = "yes"
    EXPOSURE_NO = "no"
    EXPOSURE_NOT_SURE = "not_sure"
    EXPOSURE_CHOICES = (
        (EXPOSURE_YES, "Yes"),
        (EXPOSURE_NO, "No"),
        (EXPOSURE_NOT_SURE, "Not sure"),
    )

    RISK_LOW = "low"
    RISK_MODERATE = "moderate"
    RISK_HIGH = "high"
    RISK_CRITICAL = "critical"
    RISK_CHOICES = (
        (RISK_LOW, "Low"),
        (RISK_MODERATE, "Moderate"),
        (RISK_HIGH, "High"),
        (RISK_CRITICAL, "Critical"),
    )

    GENDER_MALE = "male"
    GENDER_FEMALE = "female"
    GENDER_OTHER = "other"
    GENDER_NOT_SAY = "not_say"
    GENDER_CHOICES = (
        (GENDER_MALE, "Male"),
        (GENDER_FEMALE, "Female"),
        (GENDER_OTHER, "Other"),
        (GENDER_NOT_SAY, "Rather not say"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    deduplication_id = models.CharField(max_length=255, default=uuid.uuid4, unique=True)
    msisdn = models.CharField(max_length=255, validators=[za_phone_number])
    first_name = models.CharField(max_length=255, blank=True, null=True, default=None)
    last_name = models.CharField(max_length=255, blank=True, null=True, default=None)
    source = models.CharField(max_length=255)
    province = models.CharField(max_length=6, choices=PROVINCE_CHOICES)
    city = models.CharField(max_length=255)
    age = models.CharField(max_length=5, choices=AGE_CHOICES)
    date_of_birth = models.DateField(blank=True, null=True, default=None)
    fever = models.BooleanField()
    cough = models.BooleanField()
    sore_throat = models.BooleanField()
    difficulty_breathing = models.BooleanField(null=True, blank=True, default=None)
    exposure = models.CharField(max_length=9, choices=EXPOSURE_CHOICES)
    confirmed_contact = models.BooleanField(blank=True, null=True, default=None)
    tracing = models.BooleanField(help_text="Whether the NDoH can contact the user")
    risk = models.CharField(max_length=8, choices=RISK_CHOICES)
    gender = models.CharField(
        max_length=7, choices=GENDER_CHOICES, blank=True, default=""
    )
    location = models.CharField(
        max_length=255, blank=True, default="", validators=[geographic_coordinate]
    )
    city_location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        default=None,
        validators=[geographic_coordinate],
    )
    muscle_pain = models.BooleanField(null=True, blank=True, default=None)
    smell = models.BooleanField(null=True, blank=True, default=None)
    preexisting_condition = models.CharField(
        max_length=9, choices=EXPOSURE_CHOICES, blank=True, default=""
    )
    rooms_in_household = models.IntegerField(blank=True, null=True, default=None)
    persons_in_household = models.IntegerField(blank=True, null=True, default=None)
    completed_timestamp = models.DateTimeField(default=timezone.now)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_by = models.CharField(max_length=255, blank=True, default="")
    data = JSONField(default=dict, blank=True, null=True)


class CDUAddressUpdate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.CharField(max_length=255, blank=True, default="")
    timestamp = models.DateTimeField(default=timezone.now)
    msisdn = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    id_type = models.CharField(max_length=8, choices=IDTYPES)
    id_number = models.CharField(max_length=13, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    folder_number = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    municipality = models.CharField(max_length=255)
    city = models.CharField(max_length=255, blank=True, null=True)
    suburb = models.CharField(max_length=255)
    street_name = models.CharField(max_length=255)
    street_number = models.CharField(max_length=255)
