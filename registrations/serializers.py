from rest_framework import serializers

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
