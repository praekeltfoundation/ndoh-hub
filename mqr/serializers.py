from rest_framework import serializers


class MqrStrataSerializer(serializers.Serializer):
    facility_code = serializers.CharField(required=True)
    estimated_delivery_date = serializers.CharField(required=True)
    mom_age = serializers.CharField(required=True)


class NextMessageSerializer(serializers.Serializer):
    edd_or_dob_date = serializers.DateField(required=True)
    subscription_type = serializers.CharField(required=True)
    arm = serializers.CharField(required=True)
    sequence = serializers.CharField(required=False)


class FaqSerializer(serializers.Serializer):
    tag = serializers.CharField(required=True)
    faq_number = serializers.IntegerField(required=True)
