import re

from rest_framework import serializers

from .utils import assessmentkeywords, choiceTypeKeywords, inputTypeKeywords


class SymptomCheckSerializer(serializers.Serializer):
    whatsappid = serializers.CharField(required=True)


class AdaInputTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        user_input = data["value"].upper()
        length = len(data["value"])
        format = data["formatType"]
        max = data["max"]
        max_error = data["max_error"]
        min = data["min"]
        min_error = data["min_error"]
        pattern = data["pattern"]
        keywords = inputTypeKeywords()
        if user_input not in keywords:
            if length < 1 or length > 100:
                error = (
                    "We are sorry, your reply should be between "
                    "*1* and *100* characters."
                )
                data["error"] = error
                raise serializers.ValidationError(data)
            has_numbers = any(i.isdigit() for i in user_input)
            if format == "string":
                has_numbers = any(i.isdigit() for i in user_input)
                if has_numbers:
                    error = (
                        "Sorry, we didn't understand your answer. "
                        "Your reply must only include text."
                    )
                    data["error"] = error
                    raise serializers.ValidationError(data)
                if re.match(r"^[_\W]+$", user_input):
                    error = (
                        "Sorry, we didn't understand your answer. "
                        "Your reply must be alphabetic "
                        "and not have special characters only."
                    )
                    data["error"] = error
                    raise serializers.ValidationError(data)
            elif format == "integer" and pattern != "":
                if not re.match(pattern, user_input):
                    error = min_error
                    data["error"] = error
                    raise serializers.ValidationError(data)
                elif int(user_input) > max:
                    error = max_error
                    data["error"] = error
                    raise serializers.ValidationError(data)
            elif format == "integer" and pattern == "":
                only_numbers = user_input.isdecimal()
                if not only_numbers:
                    error = (
                        "Sorry, we didn't understand your answer. "
                        "Your reply must only include numbers."
                    )
                    data["error"] = error
                    raise serializers.ValidationError(data)
                elif only_numbers:
                    if int(user_input) > max:
                        error = max_error
                        data["error"] = error
                        raise serializers.ValidationError(data)
                    elif int(user_input) < min:
                        error = min_error
                        data["error"] = error
                        raise serializers.ValidationError(data)
        return data


class AdaTextTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        keywords = assessmentkeywords()
        user_input = data["value"].upper()
        if user_input not in keywords:
            error = "Please reply *continue*, *0* or *accept* to continue."
            data["error"] = error
            raise serializers.ValidationError(data)
        return data


class StartAssessmentSerializer(serializers.Serializer):
    def validate_value(self, data):
        return data


class AdaChoiceTypeSerializer(serializers.Serializer):
    def validate_value(self, data):
        user_input = data["value"].upper()
        choices = data["choices"]
        keywords = choiceTypeKeywords()
        if user_input not in keywords:
            try:
                int(user_input)
            except ValueError:
                error = "Please reply with the number that matches your answer."
                data["error"] = error
                raise serializers.ValidationError(data)
            if not (0 < int(user_input) <= choices):
                error = (
                    f"Something seems to have gone wrong. You entered "
                    f"{user_input} but there are {choices} options. "
                    f"Please reply with a number between 1 and {choices}."
                )
                data["error"] = error
                raise serializers.ValidationError(data)
            if int(user_input) < 1:
                error = (
                    f"Something seems to have gone wrong. You entered "
                    f"{user_input}. Please select the option that "
                    f"matches your answer."
                )
                data["error"] = error
                raise serializers.ValidationError(data)
        return data


class SubmitCastorDataSerializer(serializers.Serializer):
    class CastorRecord(serializers.Serializer):
        id = serializers.CharField(required=True)
        value = serializers.CharField(required=True)

    edc_record_id = serializers.CharField(required=False, allow_null=True)
    token = serializers.CharField(required=True)
    records = serializers.ListField(
        child=CastorRecord(), allow_empty=False, required=True
    )
