from rest_framework import serializers


class InboundCheckSerializer(serializers.Serializer):
    question = serializers.CharField(required=True)


class UrgencyCheckSerializer(serializers.Serializer):
    question = serializers.CharField(required=True)
