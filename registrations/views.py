import django_filters
import json
import requests

from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from django.conf import settings

from rest_hooks.models import Hook
from rest_framework import viewsets, mixins, generics, filters, status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.response import Response

from .models import Source, Registration
from .serializers import (UserSerializer, GroupSerializer,
                          SourceSerializer, RegistrationSerializer,
                          HookSerializer, CreateUserSerializer,
                          JembiHelpdeskOutgoingSerializer)


class HookViewSet(viewsets.ModelViewSet):
    """
    Retrieve, create, update or destroy webhooks.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Hook.objects.all()
    serializer_class = HookSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserViewSet(viewsets.ReadOnlyModelViewSet):

    """
    API endpoint that allows users to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserView(APIView):
    """ API endpoint that allows users creation and returns their token.
    Only admin users can do this to avoid permissions escalation.
    """
    permission_classes = (IsAdminUser,)

    def post(self, request):
        '''Create a user and token, given an email. If user exists just
        provide the token.'''
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get('email')
        try:
            user = User.objects.get(username=email)
        except User.DoesNotExist:
            user = User.objects.create_user(email, email=email)
        token, created = Token.objects.get_or_create(user=user)

        return Response(
            status=status.HTTP_201_CREATED, data={'token': token.key})


class GroupViewSet(viewsets.ReadOnlyModelViewSet):

    """
    API endpoint that allows groups to be viewed or edited.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class SourceViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows sources to be viewed or edited.
    """
    permission_classes = (IsAdminUser,)
    queryset = Source.objects.all()
    serializer_class = SourceSerializer


class RegistrationPost(mixins.CreateModelMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer

    def post(self, request, *args, **kwargs):
        # load the users sources - posting users should only have one source
        source = Source.objects.get(user=self.request.user)
        request.data["source"] = source.id
        return self.create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user,
                        updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RegistrationFilter(filters.FilterSet):
    """Filter for registrations created, using ISO 8601 formatted dates"""
    created_before = django_filters.IsoDateTimeFilter(name="created_at",
                                                      lookup_type="lte")
    created_after = django_filters.IsoDateTimeFilter(name="created_at",
                                                     lookup_type="gte")

    class Meta:
        model = Registration
        ('reg_type', 'registrant_id', 'validated', 'source', 'created_at')
        fields = ['reg_type', 'registrant_id', 'validated', 'source',
                  'created_before', 'created_after']


class RegistrationGetViewSet(viewsets.ReadOnlyModelViewSet):
    """ API endpoint that allows Registrations to be viewed.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    filter_class = RegistrationFilter


class JembiHelpdeskOutgoingView(APIView):
    """ API endpoint that allows the helpdesk to post messages to Jembi
    """
    permission_classes = (IsAuthenticated,)

    def build_jembi_helpdesk_json(self, validated_data):

        def jembi_format_date(date):
            return date.strftime("%Y%m%d%H%M%S")

        registration = get_object_or_404(
            Registration, registrant_id=validated_data.get('user_id'))

        json_template = {
            "encdate": jembi_format_date(validated_data.get('created_on')),
            # is casepro, adding a label doesn't change the timestamp
            # (we only have created_on)
            "repdate": jembi_format_date(validated_data.get('created_on')),
            "mha": 1,
            "swt": 2,  # 1 ussd, 2 sms
            "cmsisdn": validated_data.get('to'),
            "dmsisdn": validated_data.get('to'),
            "faccode":
                registration.data.faccode
                if hasattr(registration.data, 'faccode') else '',
            "data": {
                "question": validated_data.get('content'),
                "answer": validated_data.get('reply_to'),
            },
            "class": validated_data.get('label'),
            "type": 7,  # 7 helpdesk
            "op": registration.data.operator_id
                if hasattr(registration.data, 'operator_id') else '',
        }
        return json_template

    def post(self, request):
        if not (settings.JEMBI_BASE_URL and settings.JEMBI_USERNAME and
                settings.JEMBI_PASSWORD):
            return Response(
                'Jembi integration is not configured properly.',
                status.HTTP_503_SERVICE_UNAVAILABLE)

        serializer = JembiHelpdeskOutgoingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post_data = self.build_jembi_helpdesk_json(serializer.validated_data)
        requests.post(
            '%s/helpdesk' % settings.JEMBI_BASE_URL,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(post_data),
            auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
            verify=False)

        return Response(
            status=status.HTTP_200_OK)


class HealthcheckView(APIView):

    """ Healthcheck Interaction
        GET - returns service up - getting auth'd requires DB
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        status = 200
        resp = {
            "up": True,
            "result": {
                "database": "Accessible"
            }
        }
        return Response(resp, status=status)
