from rest_framework import serializers

from registrations.fields import PhoneNumberField
from registrations.models import Registration


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registration
        read_only_fields = (
            "validated",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        )
        fields = (
            "id",
            "external_id",
            "reg_type",
            "registrant_id",
            "validated",
            "data",
            "source",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
        )


class WhatsAppContactCheckSerializer(serializers.Serializer):
    blocking = serializers.ChoiceField(
        choices=["wait", "no_wait"],
        default="no_wait",
        label="Blocking",
        help_text="Whether or not to do a background or foreground check",
    )
    contacts = serializers.ListField(
        child=PhoneNumberField(country_code="ZA"),
        label="Contacts",
        help_text="A list of phone numbers to do the contact check for",
    )
