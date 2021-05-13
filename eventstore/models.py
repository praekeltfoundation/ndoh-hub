import random
import uuid
from datetime import date
from typing import Text

import pycountry
from django.conf import settings
from django.conf.locale import LANG_INFO
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from eventstore.hcs_tasks import start_study_c_registration_flow, update_turn_contact
from eventstore.validators import (
    validate_facility_code,
    validate_sa_id_number,
    validate_true,
)
from ndoh_hub.utils import is_valid_edd_date
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
    timestamp = models.DateTimeField(auto_now=True)
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
            for l in self.data.get("_vnd", {})  # noqa: E741
            .get("v1", {})
            .get("labels", [])
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

    WORK_HEALTHCARE = "healthcare"
    WORK_EDUCATION = "education"
    WORK_PORT = "port_of_entry"
    WORK_OTHER = "other"

    WORK_CHOICES = (
        (WORK_HEALTHCARE, "Healthcare"),
        (WORK_EDUCATION, "Education"),
        (WORK_PORT, "Port of entry"),
        (WORK_OTHER, "Other"),
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
    place_of_work = models.CharField(
        max_length=13, blank=True, null=True, default=None, choices=WORK_CHOICES
    )
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

    class Meta:
        indexes = [models.Index(fields=["msisdn", "timestamp"])]

    def calculate_risk(self):
        symptoms = sum(
            [
                self.fever,
                self.cough,
                self.sore_throat,
                bool(self.difficulty_breathing),
                bool(self.muscle_pain),
                bool(self.smell),
            ]
        )

        if symptoms >= 3:
            return self.RISK_HIGH
        elif symptoms == 2:
            if self.exposure == self.EXPOSURE_YES or self.age == self.AGE_O65:
                return self.RISK_HIGH
            else:
                return self.RISK_MODERATE
        elif symptoms == 1:
            if self.exposure == self.EXPOSURE_YES:
                return self.RISK_HIGH
            else:
                return self.RISK_MODERATE
        else:
            if self.exposure == self.EXPOSURE_YES:
                return self.RISK_MODERATE
            else:
                return self.RISK_LOW


class Covid19TriageStart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    msisdn = models.CharField(max_length=255, validators=[za_phone_number])
    source = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    created_by = models.CharField(max_length=255, blank=True, default="")


class HealthCheckUserProfileManager(models.Manager):
    def get_or_prefill(self, msisdn: Text) -> "HealthCheckUserProfile":
        """
        Either gets the existing user profile, or creates one using data in the
        historical healthchecks
        """
        try:
            return self.get(msisdn=msisdn)
        except self.model.DoesNotExist:
            healthchecks = Covid19Triage.objects.filter(msisdn=msisdn).order_by(
                "completed_timestamp"
            )
            profile = self.model()
            for healthcheck in healthchecks.iterator():
                profile.update_from_healthcheck(healthcheck)
            return profile


class HealthCheckUserProfile(models.Model):
    ARM_CONTROL = "C"
    ARM_TREATMENT_1 = "T1"
    ARM_TREATMENT_2 = "T2"
    ARM_TREATMENT_3 = "T3"
    ARM_TREATMENT_4 = "T4"

    STUDY_ARM_CHOICES = (
        (ARM_CONTROL, "Control"),
        (ARM_TREATMENT_1, "Treatment 1"),
        (ARM_TREATMENT_2, "Treatment 2"),
        (ARM_TREATMENT_3, "Treatment 3"),
        (ARM_TREATMENT_4, "Treatment 4"),
    )

    STUDY_ARM_QUARANTINE_CHOICES = (
        (ARM_CONTROL, "Control"),
        (ARM_TREATMENT_1, "Treatment 1"),
        (ARM_TREATMENT_2, "Treatment 2"),
        (ARM_TREATMENT_3, "Treatment 3"),
    )

    msisdn = models.CharField(
        primary_key=True, max_length=255, validators=[za_phone_number]
    )
    first_name = models.CharField(max_length=255, blank=True, null=True, default=None)
    last_name = models.CharField(max_length=255, blank=True, null=True, default=None)
    province = models.CharField(max_length=6, choices=Covid19Triage.PROVINCE_CHOICES)
    city = models.CharField(max_length=255)
    age = models.CharField(max_length=5, choices=Covid19Triage.AGE_CHOICES)
    date_of_birth = models.DateField(blank=True, null=True, default=None)
    gender = models.CharField(
        max_length=7, choices=Covid19Triage.GENDER_CHOICES, blank=True, default=""
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
    preexisting_condition = models.CharField(
        max_length=9, choices=Covid19Triage.EXPOSURE_CHOICES, blank=True, default=""
    )
    rooms_in_household = models.IntegerField(blank=True, null=True, default=None)
    persons_in_household = models.IntegerField(blank=True, null=True, default=None)
    hcs_study_a_arm = models.CharField(
        max_length=3, choices=STUDY_ARM_CHOICES, null=True, default=None
    )
    hcs_study_c_testing_arm = models.CharField(
        max_length=3, choices=STUDY_ARM_CHOICES, null=True, default=None
    )
    hcs_study_c_quarantine_arm = models.CharField(
        max_length=3, choices=STUDY_ARM_QUARANTINE_CHOICES, null=True, default=None
    )
    data = JSONField(default=dict, blank=True, null=True)

    objects = HealthCheckUserProfileManager()

    def update_from_healthcheck(self, healthcheck: Covid19Triage) -> None:
        """
        Updates the profile with the data from the latest healthcheck
        """

        def has_value(v):
            """
            We want values like 0 and False to be considered values, but values like
            None or blank strings to not be considered values
            """
            return v or v == 0 or v is False

        for field in [
            "msisdn",
            "first_name",
            "last_name",
            "province",
            "city",
            "age",
            "date_of_birth",
            "gender",
            "location",
            "city_location",
            "preexisting_condition",
            "rooms_in_household",
            "persons_in_household",
        ]:
            value = getattr(healthcheck, field, None)
            if has_value(value):
                setattr(self, field, value)

        for k, v in healthcheck.data.items():
            if has_value(v):
                self.data[k] = v

    def update_post_screening_study_arms(self, risk, source):
        if self.age == Covid19Triage.AGE_U18:
            return

        if (
            source == "WhatsApp"
            and not self.hcs_study_a_arm
            and settings.HCS_STUDY_A_ACTIVE
        ):
            self.hcs_study_a_arm = self.get_random_study_arm()
            update_turn_contact.delay(
                self.msisdn, "hcs_study_a_arm", self.hcs_study_a_arm
            )

        if (
            not self.hcs_study_c_testing_arm
            and not self.hcs_study_c_quarantine_arm
            and settings.HCS_STUDY_C_ACTIVE
        ):
            if risk == Covid19Triage.RISK_HIGH:
                self.hcs_study_c_testing_arm = self.get_random_study_arm()
                update_turn_contact.delay(
                    self.msisdn, "hcs_study_c_arm", self.hcs_study_c_testing_arm
                )

            if risk == Covid19Triage.RISK_MODERATE:
                self.hcs_study_c_quarantine_arm = self.get_random_study_quarantine_arm()
                update_turn_contact.delay(
                    self.msisdn,
                    "hcs_study_c_quarantine_arm",
                    self.hcs_study_c_quarantine_arm,
                )

            if risk == Covid19Triage.RISK_HIGH or risk == Covid19Triage.RISK_MODERATE:
                start_study_c_registration_flow.delay(
                    self.msisdn,
                    self.hcs_study_c_testing_arm,
                    self.hcs_study_c_quarantine_arm,
                    risk,
                    source,
                )

    def get_random_study_arm(self):
        return random.choice(self.STUDY_ARM_CHOICES)[0]

    def get_random_study_quarantine_arm(self):
        return random.choice(self.STUDY_ARM_QUARANTINE_CHOICES)[0]


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


class DBEOnBehalfOfProfileManager(models.Manager):
    def update_or_create_from_healthcheck(
        self, healthcheck: Covid19Triage
    ) -> "DBEOnBehalfOfProfile":
        """
        Either updates an existing profile, or creates a new one.
        """
        return self.update_or_create(
            msisdn=healthcheck.msisdn,
            name=healthcheck.data.get("name"),
            defaults={
                "age": healthcheck.data.get("age"),
                "gender": healthcheck.gender,
                "province": healthcheck.province,
                "city": healthcheck.city,
                "city_location": healthcheck.city_location or "",
                "location": healthcheck.location,
                "school": healthcheck.data.get("school_name"),
                "school_emis": healthcheck.data.get("school_emis"),
                "preexisting_condition": healthcheck.preexisting_condition,
                "obesity": healthcheck.data.get("obesity"),
                "diabetes": healthcheck.data.get("diabetes"),
                "hypertension": healthcheck.data.get("hypertension"),
                "cardio": healthcheck.data.get("cardio"),
                "asthma": healthcheck.data.get("asthma"),
                "tb": healthcheck.data.get("tb"),
                "pregnant": healthcheck.data.get("pregnant"),
                "respiratory": healthcheck.data.get("respiratory"),
                "cardiac": healthcheck.data.get("cardiac"),
                "immuno": healthcheck.data.get("immuno"),
            },
        )


class DBEOnBehalfOfProfile(models.Model):
    msisdn = models.CharField(max_length=255, validators=[za_phone_number])
    name = models.CharField(max_length=255)
    age = models.IntegerField()
    gender = models.CharField(max_length=7, choices=Covid19Triage.GENDER_CHOICES)
    province = models.CharField(max_length=6, choices=Covid19Triage.PROVINCE_CHOICES)
    city = models.CharField(max_length=255)
    city_location = models.CharField(
        max_length=255, blank=True, default="", validators=[geographic_coordinate]
    )
    location = models.CharField(
        max_length=255, blank=True, default="", validators=[geographic_coordinate]
    )
    school = models.CharField(max_length=255)
    school_emis = models.CharField(max_length=255)
    preexisting_condition = models.CharField(
        max_length=9, choices=Covid19Triage.EXPOSURE_CHOICES
    )
    obesity = models.BooleanField(null=True, default=None)
    diabetes = models.BooleanField(null=True, default=None)
    hypertension = models.BooleanField(null=True, default=None)
    cardio = models.BooleanField(null=True, default=None)
    asthma = models.BooleanField(null=True, default=None)
    tb = models.BooleanField(null=True, default=None)
    pregnant = models.BooleanField(null=True, default=None)
    respiratory = models.BooleanField(null=True, default=None)
    cardiac = models.BooleanField(null=True, default=None)
    immuno = models.BooleanField(null=True, default=None)

    objects = DBEOnBehalfOfProfileManager()

    class Meta:
        indexes = [models.Index(fields=["msisdn"])]


class MomConnectImport(models.Model):
    class Status:
        VALIDATING = 0
        VALIDATED = 1
        UPLOADING = 2
        COMPLETE = 3
        ERROR = 4
        choices = (
            (VALIDATING, "Validating"),
            (VALIDATED, "Validated"),
            (UPLOADING, "Uploading"),
            (COMPLETE, "Complete"),
            (ERROR, "Error"),
        )

    timestamp = models.DateTimeField(auto_now=True)
    status = models.PositiveSmallIntegerField(
        choices=Status.choices, default=Status.VALIDATING
    )
    last_uploaded_row = models.PositiveSmallIntegerField(default=0)


class ImportError(models.Model):
    class ErrorType:
        INVALID_FILETYPE = 0
        INVALID_HEADER = 1
        FIELD_VALIDATION_ERROR = 2
        ROW_VALIDATION_ERROR = 3
        OPTED_OUT_ERROR = 4
        ALREADY_REGISTERED = 5
        choices = (
            (INVALID_FILETYPE, "File is not a CSV"),
            (INVALID_HEADER, "Fields {} not found in header"),
            (FIELD_VALIDATION_ERROR, "Field {} failed validation: {}"),
            (ROW_VALIDATION_ERROR, "Failed validation: {}"),
            (OPTED_OUT_ERROR, "Mother is opted out and has not chosen to opt in again"),
            (ALREADY_REGISTERED, "Mother is already receiving prebirth messages"),
        )

    mcimport = models.ForeignKey(
        to=MomConnectImport, on_delete=models.CASCADE, related_name="errors"
    )
    row_number = models.PositiveSmallIntegerField()
    error_type = models.PositiveSmallIntegerField(choices=ErrorType.choices)
    error_args = JSONField(blank=True)

    @property
    def error(self):
        return self.get_error_type_display().format(*self.error_args)


class ImportRow(models.Model):
    class IDType:
        SAID = 0
        PASSPORT = 1
        NONE = 2
        choices = ((SAID, "SA ID"), (PASSPORT, "Passport"), (NONE, "None"))

    class PassportCountry:
        ZW = 0
        MZ = 1
        MW = 2
        NG = 3
        CD = 4
        SO = 5
        OTHER = 6
        choices = (
            (ZW, "Zimbabwe"),
            (MZ, "Mozambique"),
            (MW, "Malawi"),
            (NG, "Nigeria"),
            (CD, "DRC"),
            (SO, "Somalia"),
            (OTHER, "Other"),
        )

    class Language:
        ZUL = 0
        XHO = 1
        AFR = 2
        ENG = 3
        NSO = 4
        TSN = 5
        SOT = 6
        TSO = 7
        SSW = 8
        VEN = 9
        NBL = 10
        choices = (
            (ZUL, "isiZulu"),
            (XHO, "isiXhosa"),
            (AFR, "Afrikaans"),
            (ENG, "English"),
            (NSO, "Sesotho sa Leboa"),
            (TSN, "Setswana"),
            (SOT, "Sesotho"),
            (TSO, "Xitsonga"),
            (SSW, "SiSwati"),
            (VEN, "Tshivenda"),
            (NBL, "isiNdebele"),
        )

    mcimport = models.ForeignKey(
        to=MomConnectImport, on_delete=models.CASCADE, related_name="rows"
    )
    row_number = models.PositiveSmallIntegerField()
    msisdn = models.CharField(max_length=255, validators=[za_phone_number])
    messaging_consent = models.BooleanField(validators=[validate_true])
    research_consent = models.BooleanField(default=False)
    previous_optout = models.BooleanField(default=False)
    facility_code = models.CharField(max_length=6, validators=[validate_facility_code])
    edd_year = models.PositiveSmallIntegerField()
    edd_month = models.PositiveSmallIntegerField()
    edd_day = models.PositiveSmallIntegerField()
    id_type = models.PositiveSmallIntegerField(choices=IDType.choices)
    id_number = models.CharField(
        max_length=13, blank=True, validators=[validate_sa_id_number]
    )
    passport_country = models.PositiveSmallIntegerField(
        null=True, blank=True, choices=PassportCountry.choices
    )
    passport_number = models.CharField(max_length=255, blank=True)
    dob_year = models.PositiveSmallIntegerField(null=True, blank=True)
    dob_month = models.PositiveSmallIntegerField(null=True, blank=True)
    dob_day = models.PositiveSmallIntegerField(null=True, blank=True)
    language = models.PositiveSmallIntegerField(
        choices=Language.choices, default=Language.ENG, blank=True
    )

    def clean(self):
        try:
            edd = date(self.edd_year, self.edd_month, self.edd_day)
            if not is_valid_edd_date(edd):
                raise ValidationError("EDD must be between now and 9 months")
        except ValueError as e:
            raise ValidationError(f"Invalid EDD date, {str(e)}")
        except TypeError:
            # Should be handled by the individual field validator
            pass

        if self.id_type == self.IDType.SAID and not self.id_number:
            raise ValidationError("ID number required for SA ID ID type")
        if self.id_type == self.IDType.PASSPORT and self.passport_country is None:
            raise ValidationError("Passport country required for passport ID type")
        if self.id_type == self.IDType.PASSPORT and not self.passport_number:
            raise ValidationError("Passport number required for passport ID type")
        if self.id_type == self.IDType.NONE:
            if self.dob_year is None or self.dob_month is None or self.dob_year is None:
                raise ValidationError("Date of birth required for none ID type")

        if (
            self.dob_year is not None
            and self.dob_month is not None
            and self.dob_day is not None
        ):
            try:
                date(self.dob_year, self.dob_month, self.dob_day)
            except ValueError as e:
                raise ValidationError(f"Invalid date of birth date, {str(e)}")
