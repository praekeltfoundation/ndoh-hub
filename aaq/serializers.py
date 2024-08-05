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


class ResponseFeedbackSerializer(serializers.Serializer):
    feedback_secret_key = serializers.CharField(required=True)
    feedback_sentiment = serializers.ChoiceField(
        required=False, choices=["negative", "positive"]
    )
    feedback_text = serializers.CharField(required=False)
    query_id = serializers.IntegerField(required=True)


class SearchSerializer(serializers.Serializer):
    query_text = serializers.CharField(required=True)
    generate_llm_response = serializers.BooleanField(required=False)
    query_metadata = serializers.JSONField(required=False)
