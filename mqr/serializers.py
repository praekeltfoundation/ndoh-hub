from rest_framework import serializers


class MqrStrataSerializer(serializers.Serializer):
    province = serializers.CharField(required=True)
    weeks_pregnant = serializers.CharField(required=True)
    age = serializers.IntegerField(required=True)
    next_index = serializers.IntegerField(required=False)
    order = serializers.CharField(required=False)
