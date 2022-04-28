from rest_framework import serializers


class SymptomCheckSerializer(serializers.Serializer):
    whatsappid = serializers.CharField(required=True)


class AdaInputTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        user_input = data["value"].upper()
        length = len(data["value"])
        format = data["formatType"]
        keywords = ["0", "ACCEPT", "CONTINUE", "BACK", "MENU"]
        if user_input not in keywords:
            if length < 1 or length > 100:
                error = (
                    "We are sorry, your reply should be between "
                    "*1* and *100* characters.\n\n"
                )
                data["message"] = f"{error}{data['message']}"
                raise serializers.ValidationError(data)
            has_numbers = any(i.isdigit() for i in user_input)
            if format == "string":
                has_numbers = any(i.isdigit() for i in user_input)
                if has_numbers:
                    error = (
                        "We are sorry, you entered a number. "
                        "Please reply with text.\n\n"
                    )
                    data["message"] = f"{error}{data['message']}"
                    raise serializers.ValidationError(data)
            elif format == "integer":
                only_numbers = user_input.isdecimal()
                if not only_numbers:
                    error = (
                        "We are sorry, you entered text. "
                        "Please reply with a number.\n\n"
                    )
                    data["message"] = f"{error}{data['message']}"
                    raise serializers.ValidationError(data)
        return data


class AdaTextTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        keywords = ["0", "ACCEPT", "CONTINUE", "BACK", "MENU"]
        user_input = data["value"].upper()
        if user_input not in keywords:
            error = "Please reply *continue*, *0* or *accept* to continue.\n\n"
            data["message"] = f"{error}{data['message']}"
            raise serializers.ValidationError(data)
        return data


class StartAssessmentSerializer(serializers.Serializer):
    def validate_value(self, data):
        return data


class AdaChoiceTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        user_input = data["value"].upper()
        choices = data["choices"]
        keywords = ["0", "ACCEPT", "CONTINUE", "BACK", "MENU"]
        if user_input not in keywords:
            try:
                int(user_input)
            except ValueError:
                error = "Please reply with the number that matches your answer.\n\n"
                data["message"] = f"{error}{data['message']}"
                raise serializers.ValidationError(data)
            if not (0 <= int(user_input) <= choices):
                error = (
                    f"Something seems to have gone wrong. You entered "
                    f"{user_input} but there are only {choices} options. "
                    f"Please reply with a number between 1 and {choices}."
                )
                data["message"] = f"{error} {data['message']}"
                raise serializers.ValidationError(data)
            if int(user_input) < 1:
                error = (
                    f"Something seems to have gone wrong. You entered "
                    f"{user_input}. Please select the option that "
                    f"matches your answer."
                )
                data["message"] = f"{error} {data['message']}"
                raise serializers.ValidationError(data)
        return data
