import uuid

from rest_framework import serializers

from eventstore.models import (
    BabyDobSwitch,
    BabySwitch,
    CDUAddressUpdate,
    ChannelSwitch,
    CHWRegistration,
    Covid19Triage,
    DBEOnBehalfOfProfile,
    EddSwitch,
    HealthCheckUserProfile,
    IdentificationSwitch,
    LanguageSwitch,
    MSISDNSwitch,
    OptOut,
    PMTCTRegistration,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
    ResearchOptinSwitch,
)
from registrations.serializers import MSISDNField
from registrations.validators import posix_timestamp


class BaseEventSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user.username
        return super().create(validated_data)


class OptOutSerializer(BaseEventSerializer):
    class Meta:
        model = OptOut
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class BabySwitchSerializer(BaseEventSerializer):
    class Meta:
        model = BabySwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class ChannelSwitchSerializer(BaseEventSerializer):
    class Meta:
        model = ChannelSwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class MSISDNSwitchSerializer(BaseEventSerializer):
    class Meta:
        model = MSISDNSwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class LanguageSwitchSerializer(BaseEventSerializer):
    class Meta:
        model = LanguageSwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class IdentificationSwitchSerializer(BaseEventSerializer):
    class Meta:
        model = IdentificationSwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class ResearchOptinSwitchSerializer(BaseEventSerializer):
    class Meta:
        model = ResearchOptinSwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class PublicRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = PublicRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class CHWRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = CHWRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class PrebirthRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = PrebirthRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class PostbirthRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = PostbirthRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class PMTCTRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = PMTCTRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class Covid19TriageSerializer(BaseEventSerializer):
    msisdn = MSISDNField(country="ZA")
    deduplication_id = serializers.CharField(default=uuid.uuid4, max_length=255)

    class Meta:
        model = Covid19Triage
        fields = (
            "id",
            "deduplication_id",
            "msisdn",
            "source",
            "province",
            "city",
            "age",
            "fever",
            "cough",
            "sore_throat",
            "difficulty_breathing",
            "exposure",
            "tracing",
            "risk",
            "gender",
            "location",
            "muscle_pain",
            "smell",
            "preexisting_condition",
            "completed_timestamp",
            "timestamp",
            "created_by",
            "data",
        )
        read_only_fields = ("id", "created_by")


class Covid19TriageV2Serializer(BaseEventSerializer):
    msisdn = MSISDNField(country="ZA")
    deduplication_id = serializers.CharField(default=uuid.uuid4, max_length=255)

    class Meta:
        model = Covid19Triage
        fields = (
            "id",
            "deduplication_id",
            "msisdn",
            "first_name",
            "last_name",
            "source",
            "province",
            "city",
            "age",
            "date_of_birth",
            "fever",
            "cough",
            "sore_throat",
            "difficulty_breathing",
            "exposure",
            "confirmed_contact",
            "tracing",
            "risk",
            "gender",
            "location",
            "city_location",
            "muscle_pain",
            "smell",
            "preexisting_condition",
            "rooms_in_household",
            "persons_in_household",
            "completed_timestamp",
            "timestamp",
            "created_by",
            "data",
        )
        read_only_fields = ("id", "created_by")


class Covid19TriageV3Serializer(BaseEventSerializer):
    msisdn = MSISDNField(country="ZA")
    deduplication_id = serializers.CharField(default=uuid.uuid4, max_length=255)
    place_of_work = serializers.CharField(required=False)

    class Meta:
        model = Covid19Triage
        fields = (
            "id",
            "deduplication_id",
            "msisdn",
            "first_name",
            "last_name",
            "source",
            "province",
            "city",
            "age",
            "date_of_birth",
            "fever",
            "cough",
            "sore_throat",
            "difficulty_breathing",
            "exposure",
            "confirmed_contact",
            "tracing",
            "risk",
            "gender",
            "location",
            "city_location",
            "muscle_pain",
            "smell",
            "preexisting_condition",
            "rooms_in_household",
            "persons_in_household",
            "completed_timestamp",
            "timestamp",
            "created_by",
            "data",
            "place_of_work",
        )
        read_only_fields = ("id", "created_by")


class HealthCheckUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthCheckUserProfile
        fields = "__all__"


class MSISDNSerializer(serializers.Serializer):
    msisdn = MSISDNField(country="ZA")


class CDUAddressUpdateSerializer(BaseEventSerializer):
    class Meta:
        model = CDUAddressUpdate
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class WhatsAppInboundMessageSerializer(serializers.Serializer):
    id = serializers.CharField(required=True)
    type = serializers.CharField()
    timestamp = serializers.CharField(validators=[posix_timestamp])


setattr(WhatsAppInboundMessageSerializer, "from", serializers.CharField())


class WhatsAppEventSerializer(serializers.Serializer):
    id = serializers.CharField(required=True)
    recipient_id = serializers.CharField()
    timestamp = serializers.CharField(validators=[posix_timestamp])
    status = serializers.CharField()


class WhatsAppWebhookSerializer(serializers.Serializer):
    messages = serializers.ListField(
        child=WhatsAppInboundMessageSerializer(), allow_empty=True, required=False
    )
    statuses = serializers.ListField(
        child=WhatsAppEventSerializer(), allow_empty=True, required=False
    )


class TurnOutboundSerializer(serializers.Serializer):
    to = serializers.CharField()


class EddSwitchSerializer(BaseEventSerializer):
    class Meta:
        model = EddSwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class BabyDobSwitchSerializer(BaseEventSerializer):
    class Meta:
        model = BabyDobSwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class DBEOnBehalfOfProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DBEOnBehalfOfProfile
        fields = "__all__"
