from rest_framework import serializers


class InboundCheckSerializer(serializers.Serializer):
    question = serializers.CharField(required=True)


class UrgencyCheckSerializer(serializers.Serializer):
    question = serializers.CharField(required=True)


class AddFeedbackSerializer(serializers.Serializer):
    class Feedback(serializers.Serializer):
        feedback_type = serializers.ChoiceField(choices=("positive", "negative"))
        faq_id = serializers.CharField(required=False)
        page_number = serializers.CharField(required=False)

    feedback_secret_key = serializers.CharField(required=True)
    inbound_id = serializers.CharField(required=True)
    feedback = Feedback()

    def validate(self, data):
        faq_id = data["feedback"].get("faq_id")
        page_number = data["feedback"].get("page_number")
        if not faq_id and not page_number:
            raise serializers.ValidationError(
                "At least one of faq_id or page_number must be supplied."
            )

        return data
