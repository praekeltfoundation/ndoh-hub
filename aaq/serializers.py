from rest_framework import serializers


class InboundCheckSerializer(serializers.Serializer):
    question = serializers.CharField(required=True)


class PaginatedResponseSerializer(serializers.Serializer):
    inbound_id = serializers.IntegerField(required=True)
