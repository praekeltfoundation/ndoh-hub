from django.contrib.auth.models import User, Group
from .models import Source, Registration
from rest_framework import serializers
from rest_hooks.models import Hook


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class CreateUserSerializer(serializers.Serializer):
    email = serializers.EmailField()


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


class SourceSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = Source
        read_only_fields = ('created_at', 'updated_at')
        fields = ('url', 'id', 'name', 'user', 'authority', 'created_at',
                  'updated_at')


class RegistrationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Registration
        read_only_fields = ('validated', 'created_by', 'updated_by',
                            'created_at', 'updated_at')
        fields = ('id', 'reg_type', 'registrant_id', 'validated', 'data',
                  'source', 'created_at', 'updated_at', 'created_by',
                  'updated_by')


class HookSerializer(serializers.ModelSerializer):

    class Meta:
        model = Hook
        read_only_fields = ('user',)


class ThirdPartyRegistrationSerializer(serializers.Serializer):
    hcw_msisdn = serializers.CharField()
    mom_msisdn = serializers.CharField()
    mom_id_type = serializers.CharField()
    mom_passport_origin = serializers.CharField(allow_null=True)
    mom_lang = serializers.CharField()
    mom_edd = serializers.CharField()
    mom_id_no = serializers.CharField()
    mom_dob = serializers.CharField()
    clinic_code = serializers.CharField(allow_null=True)
    authority = serializers.CharField()
    consent = serializers.BooleanField()
    mha = serializers.IntegerField()
    swt = serializers.IntegerField()
