from datetime import datetime

import phonenumbers
from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_hooks.models import Hook

from changes.fields import PhoneNumberField
from changes.serializers import ChangeSerializer
from ndoh_hub import utils
from registrations import validators
from registrations.models import PositionTracker

from .models import Registration, Source


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ("url", "username", "email", "groups")


class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ("url", "name")


class SourceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Source
        read_only_fields = ("created_at", "updated_at")
        fields = ("url", "id", "name", "user", "authority", "created_at", "updated_at")


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        read_only_fields = (
            "validated",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        fields = (
            "id",
            "external_id",
            "reg_type",
            "registrant_id",
            "validated",
            "data",
            "source",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )


class HookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hook
        read_only_fields = ("user",)
        exclude = ()


class MSISDNField(serializers.CharField):
    """
    A phone number, validated using the phonenumbers library
    """

    def __init__(self, *args, **kwargs):
        self.country = kwargs.pop("country", None)
        return super(MSISDNField, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        number = phonenumbers.parse(obj, self.country)
        return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)

    def to_internal_value(self, data):
        try:
            number = phonenumbers.parse(data, self.country)
        except phonenumbers.NumberParseException as e:
            raise serializers.ValidationError(str(e))
        if not phonenumbers.is_possible_number(number):
            raise serializers.ValidationError("Not a possible phone number")
        if not phonenumbers.is_valid_number(number):
            raise serializers.ValidationError("Not a valid phone number")
        return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


class ThirdPartyRegistrationSerializer(serializers.Serializer):
    hcw_msisdn = MSISDNField(
        country="ZA", required=False, allow_null=True, allow_blank=True
    )
    mom_msisdn = MSISDNField(country="ZA")
    mom_id_type = serializers.ChoiceField(
        utils.ID_TYPES, required=False, allow_null=True, allow_blank=True
    )
    mom_passport_origin = serializers.ChoiceField(
        utils.PASSPORT_ORIGINS, required=False, allow_null=True, allow_blank=True
    )
    mom_lang = serializers.ChoiceField(utils.JEMBI_LANGUAGES)
    mom_edd = serializers.DateField(
        validators=(validators.edd,),
        input_formats=("%Y-%m-%d", "iso-8601"),
        required=False,
        allow_null=True,
    )
    mom_id_no = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    mom_dob = serializers.DateField(required=False, allow_null=True)
    clinic_code = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    authority = serializers.ChoiceField(
        choices=("chw", "clinic", "patient"),
        default="patient",
        required=False,
        allow_null=True,
        allow_blank=True,
    )
    consent = serializers.BooleanField(validators=(validators.consent,))
    mha = serializers.IntegerField(required=False, allow_null=True)
    swt = serializers.IntegerField(required=False, allow_null=True)
    encdate = serializers.DateTimeField(
        required=False,
        input_formats=["%Y%m%d%H%M%S", "iso-8601"],
        allow_null=True,
        default=timezone.now,
    )

    def validate(self, data):
        if data["authority"] == "clinic":
            clinic_fields = ("mom_id_type", "mom_edd", "clinic_code")
            if not all(data.get(f) for f in clinic_fields):
                raise serializers.ValidationError(
                    f"{clinic_fields} fields must be supplied if authority is clinic"
                )
        if data["authority"] == "chw":
            if not data.get("mom_id_type"):
                raise serializers.ValidationError(
                    "mom_id_type field must be supplied if authority is chw"
                )
        if data.get("mom_id_type") == "sa_id":
            if not data.get("mom_id_no"):
                raise serializers.ValidationError(
                    "mom_id_no field must be supplied if mom_id_type is sa_id"
                )
            validators.sa_id_no(data["mom_id_no"])
            data["mom_dob"] = data.get(
                "mom_dob",
                datetime.strptime(data["mom_id_no"][:6], "%y%m%d").strftime("%Y-%m-%d"),
            )
        elif data.get("mom_id_type") == "passport":
            if not data.get("mom_id_no"):
                raise serializers.ValidationError(
                    "mom_id_no field must be supplied if mom_id_type is passport"
                )
            if not data.get("mom_passport_origin"):
                raise serializers.ValidationError(
                    "mom_passport_origin field must be supplied if mom_id_type is "
                    "passport"
                )
            validators.passport_no(data["mom_id_no"])
        elif data.get("mom_id_type") == "none":
            if not data.get("mom_dob"):
                raise serializers.ValidationError(
                    "mom_dob must be supplied if mom_id_type is none"
                )
        data["hcw_msisdn"] = data.get("hcw_msisdn", data["mom_msisdn"])
        return data


class JembiAppRegistrationSerializer(serializers.Serializer):
    external_id = serializers.CharField(
        required=False,
        default=None,
        allow_null=True,
        allow_blank=True,
        max_length=100,
        help_text="The ID of the registration in the external "
        "application that created this registration",
        validators=[UniqueValidator(queryset=Registration.objects.all())],
    )
    mom_given_name = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="The given name of the mother",
        label="Mother Given Name",
    )
    mom_family_name = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="The family name of the mother",
        label="Mother Family Name",
    )
    mom_msisdn = MSISDNField(
        country="ZA",
        help_text="The phone number of the mother",
        label="Mother MSISDN",
        source="msisdn_registrant",
    )
    hcw_msisdn = MSISDNField(
        country="ZA",
        help_text=(
            "The phone number of the Health Care Worker that registered" "the mother"
        ),
        label="Health Care Worker MSISDN",
        source="msisdn_device",
    )
    mom_id_type = serializers.ChoiceField(
        utils.ID_TYPES,
        label="Mother ID Type",
        help_text="The type of identification that the mother registered with",
        source="id_type",
    )
    mom_sa_id_no = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Mother SA ID Number",
        help_text=(
            "The SA ID number that the mother used to register. Required if "
            "mom_id_type is sa_id"
        ),
        validators=[validators.sa_id_no],
        source="sa_id_no",
    )
    mom_passport_no = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Mother passport number",
        help_text=(
            "The passport number that the mother used to register. Required "
            "if mom_id_type is passport"
        ),
        validators=[validators.passport_no],
        source="passport_no",
    )
    mom_passport_origin = serializers.ChoiceField(
        utils.PASSPORT_ORIGINS,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Mother passport origin",
        help_text=(
            "The country of origin for the mother's passport. Required if "
            "mom_id_type is passport."
        ),
        source="passport_origin",
    )
    mom_dob = serializers.DateField(
        help_text="When the mother was born", label="Mother date of birth"
    )
    mom_lang = serializers.ChoiceField(
        utils.LANGUAGES,
        help_text=(
            "The language that the mother would like to receive communication " "in"
        ),
        label="Mother language",
        source="language",
    )
    mom_email = serializers.EmailField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="The email address of the mother",
        label="Mother email",
    )
    mom_edd = serializers.DateField(
        help_text=(
            "The expected delivery date of the mother's baby. Must be in the "
            "future, but less than 43 weeks away."
        ),
        label="Mother EDD",
        validators=[validators.edd],
        source="edd",
    )
    mom_consent = serializers.BooleanField(
        default=False,
        label="Mother Consent",
        validators=[validators.consent],
        help_text=(
            "Whether the mother consented to us storing their information and "
            "sending them messsages, possibly on weekends and public "
            "holidays. Must be true"
        ),
        source="consent",
    )
    mom_opt_in = serializers.BooleanField(
        default=False,
        label="Mother opt-in",
        help_text=(
            "If the mother has previously opted out, whether or not to opt "
            "the mother back in again to continue with the registration"
        ),
    )
    mom_pmtct = serializers.BooleanField(
        default=False,
        label="Mother PMTCT messaging",
        help_text=(
            "Whether the mother would like to receive information about "
            "the prevention of mother-to-child transmission of HIV/AIDS"
        ),
    )
    mom_whatsapp = serializers.BooleanField(
        default=False,
        label="Mother WhatsApp messaging",
        help_text=(
            "If the mother is registered on the WhatsApp service, whether or "
            "not to send her messages over WhatsApp instead of SMS"
        ),
    )
    clinic_code = serializers.CharField(
        help_text="The code of the clinic where the mother was registered",
        label="Clinic Code",
        source="faccode",
    )
    mha = serializers.IntegerField(
        help_text="The ID for the application that created this registration",
        label="Mobile Health Application ID",
    )
    callback_url = serializers.URLField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="The URL to call back with the results of the registration",
        label="Callback URL",
    )
    callback_auth_token = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text=(
            "The authorization token to use when calling back with the "
            "results of the registration"
        ),
        label="Callback authorization token",
    )
    created = serializers.DateTimeField(
        help_text="The timestamp when the registration was created", label="Created at"
    )

    def validate(self, data):
        if data["id_type"] == "sa_id":
            if not data.get("sa_id_no"):
                raise serializers.ValidationError(
                    "mom_sa_id_no field must be supplied if mom_id_type is " "sa_id"
                )
        elif data["id_type"] == "passport":
            if not data.get("passport_no"):
                raise serializers.ValidationError(
                    "mom_passport_no field must be supplied if mom_id_type is "
                    "passport"
                )
            if not data.get("passport_origin"):
                raise serializers.ValidationError(
                    "mom_passport_origin field must be supplied if "
                    "mom_id_type is passport"
                )
        return data


class JembiHelpdeskOutgoingSerializer(serializers.Serializer):
    to = serializers.CharField()
    reply_to = serializers.CharField(allow_blank=True)
    content = serializers.CharField()
    user_id = serializers.CharField()
    helpdesk_operator_id = serializers.IntegerField()
    label = serializers.CharField(allow_blank=True)
    inbound_created_on = serializers.DateTimeField()
    outbound_created_on = serializers.DateTimeField()
    inbound_channel_id = serializers.CharField(required=False, allow_blank=True)
    message_id = serializers.IntegerField()


class PositionTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionTracker
        fields = ("url", "label", "position")


class EngageContextSerializer(serializers.Serializer):
    class Chat(serializers.Serializer):
        owner = PhoneNumberField(country_code="ZA")

    chat = Chat()


class EngageActionSerializer(serializers.Serializer):
    address = PhoneNumberField(country_code="ZA")
    integration_uuid = serializers.CharField()
    integration_action_uuid = serializers.CharField()
    payload = ChangeSerializer()


class WhatsAppContactCheckSerializer(serializers.Serializer):
    blocking = serializers.ChoiceField(
        choices=["wait", "no_wait"],
        default="no_wait",
        label="Blocking",
        help_text="Whether or not to do a background or foreground check",
    )
    contacts = serializers.ListField(
        child=PhoneNumberField(country_code="ZA"),
        label="Contacts",
        help_text="A list of phone numbers to do the contact check for",
    )


class SubscriptionsCheckSerializer(serializers.Serializer):
    msisdn = PhoneNumberField(country_code="ZA")


class BaseRapidProClinicRegistrationSerializer(serializers.Serializer):
    mom_msisdn = MSISDNField(
        country="ZA", help_text="The phone number of the mother", label="Mother MSISDN"
    )
    device_msisdn = MSISDNField(
        country="ZA",
        help_text="The phone number of the device that registered the mother",
        label="Registration Device MSISDN",
    )
    mom_id_type = serializers.ChoiceField(
        utils.ID_TYPES,
        label="Mother ID Type",
        help_text="The type of identification that the mother registered with",
    )
    mom_lang = serializers.ChoiceField(
        utils.LANGUAGES,
        help_text="The language that the mother would like to receive communication in",
        label="Mother language",
    )
    registration_type = serializers.ChoiceField(
        ["prebirth", "postbirth"],
        help_text="Whether this is a prebirth or postbirt registration",
        label="Registration type",
    )
    clinic_code = serializers.CharField(
        help_text="The code of the clinic where the mother was registered",
        label="Clinic Code",
    )
    channel = serializers.ChoiceField(
        ["WhatsApp", "SMS"],
        help_text="Whether this registration is for SMS or for WhatsApp",
        label="Messaging Channel",
    )
    created = serializers.DateTimeField(
        help_text="The timestamp when the registration was created", label="Created at"
    )


class SaIdNoRapidProClinicRegistrationSerializer(serializers.Serializer):
    mom_sa_id_no = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Mother SA ID Number",
        help_text="The SA ID number that the mother used to register. Required if "
        "mom_id_type is sa_id",
        validators=[validators.sa_id_no],
    )


class PassportRapidProClinicRegistrationSerializer(serializers.Serializer):
    mom_passport_no = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Mother passport number",
        help_text="The passport number that the mother used to register. Required if "
        "mom_id_type is passport",
        validators=[validators.passport_no],
    )
    mom_passport_origin = serializers.ChoiceField(
        utils.PASSPORT_ORIGINS,
        required=False,
        allow_null=True,
        allow_blank=True,
        label="Mother passport origin",
        help_text="The country of origin for the mother's passport. Required if "
        "mom_id_type is passport.",
    )


class DoBRapidProClinicRegistrationSerializer(serializers.Serializer):
    mom_dob = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="When the mother was born. Required if ID type is none",
        label="Mother date of birth",
        input_formats=["%d-%m-%Y", "iso-8601"],
    )


class PrebirthRapidProClinicRegistrationSerializer(serializers.Serializer):
    mom_edd = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="The expected delivery date of the mother's baby. Must be in the "
        "future, but less than 43 weeks away. Required if registration_type is "
        "prebirth",
        label="Mother EDD",
        validators=[validators.edd],
        input_formats=["%d-%m-%Y", "iso-8601"],
    )


class PostBirthRapidProClinicRegistrationSerializer(serializers.Serializer):
    baby_dob = serializers.DateField(
        required=False,
        allow_null=True,
        help_text="The baby's date of birth. Must be in the past, but less than 2 "
        "years. Required if registration_type is postbirth",
        label="Mother EDD",
        validators=[validators.baby_dob],
        input_formats=["%d-%m-%Y", "iso-8601"],
    )


class RapidProPublicRegistrationSerializer(serializers.Serializer):
    mom_msisdn = MSISDNField(
        country="ZA", help_text="The phone number of the mother", label="Mother MSISDN"
    )
    mom_lang = serializers.ChoiceField(
        utils.LANGUAGES,
        help_text="The language that the mother would like to receive communication in",
        label="Mother language",
    )
    created = serializers.DateTimeField(
        help_text="The timestamp when the registration was created", label="Created at"
    )
