import base64
import hmac
import django_filters
import django_filters.rest_framework as filters
from hashlib import sha256
from rest_framework import viewsets, mixins, generics, status
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import (
    IsAuthenticated, AllowAny, DjangoModelPermissions
)
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Source, Change
from .serializers import (
    ChangeSerializer, AdminOptoutSerializer, AdminChangeSerializer,
    ReceiveWhatsAppEventSerializer,
)
from seed_services_client.stage_based_messaging import StageBasedMessagingApiClient  # noqa
from django.conf import settings

from changes import tasks
from ndoh_hub.utils import TokenAuthQueryString


class CreatedAtCursorPagination(CursorPagination):
    ordering = "-created_at"


class ChangePost(mixins.CreateModelMixin, generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    queryset = Change.objects.all()
    serializer_class = ChangeSerializer

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


class ChangeFilter(filters.FilterSet):
    """Filter for changes created, using ISO 8601 formatted dates"""
    created_before = django_filters.IsoDateTimeFilter(name="created_at",
                                                      lookup_expr="lte")
    created_after = django_filters.IsoDateTimeFilter(name="created_at",
                                                     lookup_expr="gte")

    class Meta:
        model = Change
        ('action', 'registrant_id', 'validated', 'source', 'created_at')
        fields = ['action', 'registrant_id', 'validated', 'source',
                  'created_before', 'created_after']


class ChangeGetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Changes to be viewed.
    """
    permission_classes = (IsAuthenticated,)
    queryset = Change.objects.all()
    serializer_class = ChangeSerializer
    filter_class = ChangeFilter
    pagination_class = CreatedAtCursorPagination


class OptOutInactiveIdentity(APIView):
    """
    Creates an Opt-out Change for an identity we can't send messages to
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        try:
            # The hooks send the request data as {"hook":{}, "data":{}}
            data = request.data['data']
        except KeyError:
            raise ValidationError('"data" must be supplied')
        identity_id = data.get('identity_id', None)
        if identity_id is None or identity_id == "":
            raise ValidationError(
                '"identity_id" must be supplied')
        source = Source.objects.get(user=request.user)
        Change.objects.create(source=source, registrant_id=identity_id,
                              action='momconnect_nonloss_optout',
                              data={'reason': 'sms_failure'})
        return Response(status=status.HTTP_201_CREATED)


def get_or_create_source(request):
    source, created = Source.objects.get_or_create(
        user=request.user,
        defaults={
            "authority": "advisor",
            "name": (request.user.get_full_name() or
                     request.user.username)
            })
    return source


class ReceiveAdminOptout(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):

        admin_serializer = AdminOptoutSerializer(data=request.data)
        if admin_serializer.is_valid():
            identity_id = admin_serializer.validated_data["registrant_id"]
        else:
            return Response(admin_serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        sbm_client = StageBasedMessagingApiClient(
            api_url=settings.STAGE_BASED_MESSAGING_URL,
            auth_token=settings.STAGE_BASED_MESSAGING_TOKEN
        )

        active_subs = sbm_client.get_subscriptions(
            {'identity': identity_id, 'active': True}
        )["results"]

        actions = set()
        for sub in active_subs:
            messageset = sbm_client.get_messageset(sub["messageset"])
            if "nurseconnect" in messageset["short_name"]:
                actions.add("nurse_optout")
            elif "pmtct" in messageset["short_name"]:
                actions.add("pmtct_nonloss_optout")
            elif "momconnect" in messageset["short_name"]:
                actions.add("momconnect_nonloss_optout")

        source = get_or_create_source(self.request)

        request.data["source"] = source.id

        changes = []
        for action in actions:
            change = {
                "registrant_id": str(identity_id),
                "action": action,
                "data": {"reason": "other"},
                "source": source.id,
            }
            changes.append(change)

        serializer = ChangeSerializer(data=changes, many=True)

        if serializer.is_valid():
            serializer.save()

            return Response(data=serializer.data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


class ReceiveAdminChange(generics.CreateAPIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):

        admin_serializer = AdminChangeSerializer(data=request.data)
        if admin_serializer.is_valid():
            data = admin_serializer.validated_data
        else:
            return Response(admin_serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

        source = get_or_create_source(self.request)

        change = {
            "registrant_id": str(data['registrant_id']),
            "action": "admin_change_subscription",
            "data": {
                "subscription": str(data["subscription"])
            },
            "source": source.id,
        }

        if data.get('messageset'):
            change['data']['messageset'] = data['messageset']

        if data.get('language'):
            change['data']['language'] = data['language']

        serializer = ChangeSerializer(data=change)

        if serializer.is_valid():
            serializer.save()

            return Response(data=serializer.data,
                            status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


class ReceiveWhatsAppEvent(generics.GenericAPIView):
    permission_classes = (AllowAny, DjangoModelPermissions)
    queryset = Change.objects.none()
    serializer_class = ReceiveWhatsAppEventSerializer
    authentication_classes = (TokenAuthQueryString, TokenAuthentication)

    def validate_signature(self, request):
        secret = settings.ENGAGE_HMAC_SECRET
        signature = request.META.get(
            "headers", {}).get("X-Engage-Hook-Signature")

        if not signature:
            raise AuthenticationFailed(
                "X-Engage-Hook-Signature header required")

        h = hmac.new(secret.encode(), request.body, sha256)

        if base64.b64encode(h.digest()) != signature.encode():
            raise AuthenticationFailed("Invalid hook signature")

    def post(self, request, *args, **kwargs):
        self.validate_signature(request)
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # If this isn't an event that we care about
            return Response(status=status.HTTP_204_NO_CONTENT)

        for item in serializer.validated_data["statuses"]:
            tasks.process_whatsapp_unsent_event.delay(
                item["id"],
                request.user.pk,
            )

        return Response(status=status.HTTP_202_ACCEPTED)
