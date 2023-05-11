from rest_framework import serializers


class WhatsappTemplateMessageSerializer(serializers.Serializer):
    class ParametersField(serializers.Serializer):
        type = serializers.CharField(required=True)
        text = serializers.CharField(required=True)

    msisdn = serializers.CharField(required=True)
    parameters = ParametersField()
    template_name = serializers.CharField(required=True)
    namespace = serializers.CharField(required=True)
    parameters = serializers.ListField(
        child=ParametersField(), allow_empty=True, required=False
    )
