from django.utils import timezone
from rest_framework import serializers

from eventstore.serializers import MSISDNField
from mqr.models import BaselineSurveyResult


class BaselineSurveyResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaselineSurveyResult
        fields = "__all__"
        read_only_fields = ("id", "created_by")

    def update(self, instance, validated_data):
        if validated_data.get("airtime_sent"):
            validated_data["airtime_sent_at"] = timezone.now()
        super().update(instance, validated_data)
        return instance


class MqrStrataSerializer(serializers.Serializer):
    facility_code = serializers.CharField(required=True)
    estimated_delivery_date = serializers.DateField(required=True)
    mom_age = serializers.IntegerField(required=True)


class BaseMessageSerializer(serializers.Serializer):
    contact_uuid = serializers.UUIDField(required=True)
    run_uuid = serializers.UUIDField(required=True)


class NextMessageSerializer(BaseMessageSerializer):
    edd_or_dob_date = serializers.DateField(required=True)
    subscription_type = serializers.CharField(required=True)
    arm = serializers.CharField(required=True)
    mom_name = serializers.CharField(required=True)
    tag_extra = serializers.CharField(required=False, allow_blank=True)


class NextArmMessageSerializer(BaseMessageSerializer):
    last_tag = serializers.CharField(required=True)
    mom_name = serializers.CharField(required=True)
    sequence = serializers.CharField(required=True)


class FaqSerializer(BaseMessageSerializer):
    tag = serializers.CharField(required=True)
    faq_number = serializers.IntegerField(required=True)
    viewed = serializers.ListField(required=False)


class FaqMenuSerializer(serializers.Serializer):
    tag = serializers.CharField(required=True)
    menu_offset = serializers.IntegerField(required=False)


class FirstSendDateSerializer(serializers.Serializer):
    edd_or_dob_date = serializers.DateField(required=True)


class MqrEndlineChecksSerializer(serializers.Serializer):
    msisdn = MSISDNField(country="ZA")
