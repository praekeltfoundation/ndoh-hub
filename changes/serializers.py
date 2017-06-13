from .models import Change
from rest_framework import serializers


class ChangeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Change
        read_only_fields = ('validated', 'created_by', 'updated_by',
                            'created_at', 'updated_at')
        fields = ('id', 'action', 'registrant_id', 'data', 'validated',
                  'source', 'created_at', 'updated_at', 'created_by',
                  'updated_by')


class AdminOptoutSerializer(serializers.Serializer):
    registrant_id = serializers.UUIDField(allow_null=False)


class MultipleChangeSerializer(serializers.Serializer):
    changes = ChangeSerializer(many=True)

    def create(self, validated_data):
        changes_data = validated_data.pop('changes')
        changes = []
        for change_data in changes_data:
            changes.append(Change.objects.create(**change_data))
        return changes
