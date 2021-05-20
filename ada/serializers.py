from rest_framework import serializers


class SymptomCheckSerializer(serializers.Serializer):
    whatsappid = serializers.CharField(required=True)
