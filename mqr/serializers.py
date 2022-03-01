from rest_framework import serializers


class MqrStrataSerializer(serializers.Serializer):
    province = serializers.CharField(required=True)
    weeks_pregnant_bucket = serializers.CharField(required=True)
    age_bucket = serializers.CharField(required=True)
    next_index = serializers.IntegerField(required=False)
    order = serializers.CharField(required=False)
