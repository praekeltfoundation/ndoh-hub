import phonenumbers
from django.contrib.auth.models import Group, User
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


class ThirdPartyRegistrationSerializer(serializers.Serializer):
    hcw_msisdn = serializers.CharField()
    mom_msisdn = serializers.CharField()
    mom_id_type = serializers.CharField()
    mom_passport_origin = serializers.CharField(allow_null=True)
    mom_lang = serializers.CharField()
    mom_edd = serializers.CharField()
    mom_id_no = serializers.CharField()
    mom_dob = serializers.CharField()
    clinic_code = serializers.CharField(allow_null=True)
    authority = serializers.CharField()
    consent = serializers.BooleanField()
    mha = serializers.IntegerField(required=False)
    swt = serializers.IntegerField(required=False)
    encdate = serializers.CharField(required=False)


class MSISDNField(serializers.Field):
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


class PositionTrackerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PositionTracker
        fields = ("url", "label", "position")


class EngageContextSerializer(serializers.Serializer):
    class Message(serializers.Serializer):
        from_ = PhoneNumberField(country_code="ZA")

        def get_fields(self):
            # from is a reserved keyword, so we have to do a little dance
            result = super().get_fields()
            from_ = result.pop("from_")
            result["from"] = from_
            return result

    messages = serializers.ListField(child=Message(), required=False)


class EngageActionSerializer(serializers.Serializer):
    address = PhoneNumberField(country_code="ZA")
    payload = ChangeSerializer()
