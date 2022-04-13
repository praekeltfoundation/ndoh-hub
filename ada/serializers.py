from rest_framework import serializers


class SymptomCheckSerializer(serializers.Serializer):
    whatsappid = serializers.CharField(required=True)


class AdaInputTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        length = len(data["value"])
        if length < 1 or length > 100:
            error = (
                "We are sorry, your reply should be between " "1 and 100 characters."
            )
            data["message"] = f"{error} {data['message']}"
            raise serializers.ValidationError(data)
        return data


class AdaTextTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        user_input = data["value"]
        if user_input != "1" and user_input != "accept" and user_input != "continue":
            error = "Please enter 'continue', '0' or 'accept' to continue."
            data["message"] = f"{error} {data['message']}"
            raise serializers.ValidationError(data)
        return data


class StartAssessmentSerializer(serializers.Serializer):
    def validate_value(self, data):
        return data


class AdaChoiceTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        user_input = data["value"]
        choices = data["choices"]
        try:
            int(user_input)
        except ValueError:
            message = "Please enter the number that matches your answer"
            data["error"] = message
            raise serializers.ValidationError(data)
        if not (0 <= int(user_input) <= choices):
            error = (
                f"Something seems to have gone wrong. You entered "
                f"{user_input} but there are only {choices} options. "
                f"Please enter a number less than {choices}."
            )
            data["message"] = f"{error} {data['message']}"
            raise serializers.ValidationError(data)
        return data
