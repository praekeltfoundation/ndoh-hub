from rest_framework import serializers

from eventstore.models import OptOut


class OptOutSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user
        return super().create(validated_data)

    class Meta:
        model = OptOut
        fields = "__all__"
        read_only_fields = ("id", "created_by")
