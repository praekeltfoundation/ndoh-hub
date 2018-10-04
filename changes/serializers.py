from .models import Change
from rest_framework import serializers


class OneFieldRequiredValidator:
    def __init__(self, fields):
        self.fields = fields

    def set_context(self, serializer):
        self.is_create = getattr(serializer, 'instance', None) is None

    def __call__(self, data):
        if self.is_create:

            for field in self.fields:
                if data.get(field):
                    return

            raise serializers.ValidationError(
                "One of these fields must be populated: %s" %
                (', '.join(self.fields)))


class ChangeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Change
        read_only_fields = ('validated', 'created_by', 'updated_by',
                            'created_at', 'updated_at')
        fields = ('id', 'action', 'registrant_id', 'data', 'validated',
                  'source', 'created_at', 'updated_at', 'created_by',
                  'updated_by')


class AdminOptoutSerializer(serializers.Serializer):
    registrant_id = serializers.UUIDField(allow_null=False)


class AdminChangeSerializer(serializers.Serializer):
    registrant_id = serializers.UUIDField(allow_null=False)
    subscription = serializers.UUIDField(allow_null=False)
    messageset = serializers.CharField(required=False)
    language = serializers.CharField(required=False)

    validators = [OneFieldRequiredValidator(['messageset', 'language'])]


class ReceiveWhatsAppEventSerializer(serializers.Serializer):

    class StatusSerializer(serializers.Serializer):

        class ErrorSerializer(serializers.Serializer):
            code = serializers.IntegerField(required=False)
            title = serializers.CharField(required=True)

        id = serializers.CharField(required=True)
        status = serializers.ChoiceField(
            ["failed", "sent", "delivered", "read"])
        errors = serializers.ListField(child=ErrorSerializer(), default=[])

    statuses = serializers.ListField(child=StatusSerializer(), min_length=1)

    def to_internal_value(self, data):
        if "statuses" in data:
            statuses = []
            for status in data["statuses"]:
                if(status["status"] == "failed"):
                    statuses.append(status)

            data["statuses"] = statuses

        return super(ReceiveWhatsAppEventSerializer, self).to_internal_value(
            data)


class ReceiveWhatsAppSystemEventSerializer(serializers.Serializer):

    class EventSerializer(serializers.Serializer):
        type = serializers.CharField(required=True)
        message_id = serializers.CharField(required=True)
        recipient_id = serializers.CharField(required=True)

    events = serializers.ListField(child=EventSerializer(), min_length=1)
