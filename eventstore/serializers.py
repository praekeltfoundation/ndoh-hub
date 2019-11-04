from rest_framework import serializers

from eventstore.models import (
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
    OptOut,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
)


class BaseEventSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        validated_data["created_by"] = self.context["request"].user.username
        return super().create(validated_data)


class OptOutSerializer(BaseEventSerializer):
    class Meta:
        model = OptOut
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class BabySwitchSerializer(BaseEventSerializer):
    class Meta:
        model = BabySwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class ChannelSwitchSerializer(BaseEventSerializer):
    class Meta:
        model = ChannelSwitch
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class PublicRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = PublicRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class CHWRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = CHWRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class PrebirthRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = PrebirthRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")


class PostbirthRegistrationSerializer(BaseEventSerializer):
    class Meta:
        model = PostbirthRegistration
        fields = "__all__"
        read_only_fields = ("id", "created_by")
