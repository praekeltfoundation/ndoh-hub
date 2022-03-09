from rest_framework import serializers


class MqrStrataSerializer(serializers.Serializer):
    province = serializers.CharField(required=True)
    weeks_pregnant_bucket = serializers.CharField(required=True)
    age_bucket = serializers.CharField(required=True)


class NextMessageSerializer(serializers.Serializer):
    edd_or_dob_date = serializers.DateField(required=True)
    subscription_type = serializers.CharField(required=True)
    arm = serializers.CharField(required=True)
    mom_name = serializers.CharField(required=True)
    sequence = serializers.CharField(required=False)


class FaqSerializer(serializers.Serializer):
    tag = serializers.CharField(required=True)
    faq_number = serializers.IntegerField(required=True)
    viewed = serializers.ListField(required=False)
