from django.contrib.auth.models import User, Group
from .models import Source, Registration
import phonenumbers
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
    mha = serializers.IntegerField(required=False)
    swt = serializers.IntegerField(required=False)
    encdate = serializers.CharField(required=False)


class MSISDNField(serializers.Field):
    """
    A phone number, validated using the phonenumbers library
    """
    def __init__(self, *args, **kwargs):
        self.country = kwargs.pop('country', None)
        return super(MSISDNField, self).__init__(*args, **kwargs)

    def to_representation(self, obj):
        number = phonenumbers.parse(obj, self.country)
        return phonenumbers.format_number(
            number, phonenumbers.PhoneNumberFormat.E164)

    def to_internal_value(self, data):
        try:
            number = phonenumbers.parse(data, self.country)
        except phonenumbers.NumberParseException as e:
            raise serializers.ValidationError(e.message)
        if not phonenumbers.is_possible_number(number):
            raise serializers.ValidationError('Not a possible phone number')
        if not phonenumbers.is_valid_number(number):
            raise serializers.ValidationError('Not a valid phone number')
        return phonenumbers.format_number(
            number, phonenumbers.PhoneNumberFormat.E164)


class JembiHelpdeskOutgoingSerializer(serializers.Serializer):
    to = serializers.CharField()
    reply_to = serializers.CharField(allow_blank=True)
    content = serializers.CharField()
    user_id = serializers.CharField()
    helpdesk_operator_id = serializers.IntegerField()
    label = serializers.CharField(allow_blank=True)
    inbound_created_on = serializers.DateTimeField()
    outbound_created_on = serializers.DateTimeField()
    inbound_channel_id = serializers.CharField(required=False,
                                               allow_blank=True)
