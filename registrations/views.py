import base64
import datetime
import hmac
import json
import logging
from functools import partial
from hashlib import sha256
from typing import Tuple
from uuid import UUID

import django_filters
import django_filters.rest_framework as filters
import phonenumbers
import requests
from demands import HTTPServiceError
from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from requests.exceptions import RequestException
from rest_framework import generics, mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework.pagination import CursorPagination
from rest_framework.permissions import (
    DjangoModelPermissions,
    IsAdminUser,
    IsAuthenticated,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import Serializer
from rest_framework.utils.encoders import JSONEncoder
from rest_framework.views import APIView
from rest_hooks.models import Hook
from seed_services_client.identity_store import IdentityStoreApiClient
from seed_services_client.stage_based_messaging import StageBasedMessagingApiClient

from changes.models import Change
from changes.serializers import ChangeSerializer
from ndoh_hub.utils import get_available_metrics, is_client, sbm_client

from .models import PositionTracker, Registration, Source, WhatsAppContact
from .serializers import (
    BaseRapidProClinicRegistrationSerializer,
    CreateUserSerializer,
    DoBRapidProClinicRegistrationSerializer,
    EngageActionSerializer,
    EngageContextSerializer,
    GroupSerializer,
    HookSerializer,
    JembiAppRegistrationSerializer,
    JembiHelpdeskOutgoingSerializer,
    PassportRapidProClinicRegistrationSerializer,
    PositionTrackerSerializer,
    PostBirthRapidProClinicRegistrationSerializer,
    PrebirthRapidProClinicRegistrationSerializer,
    RapidProPublicRegistrationSerializer,
    RegistrationSerializer,
    SaIdNoRapidProClinicRegistrationSerializer,
    SourceSerializer,
    SubscriptionsCheckSerializer,
    ThirdPartyRegistrationSerializer,
    UserSerializer,
    WhatsAppContactCheckSerializer,
)
from .tasks import (
    create_rapidpro_clinic_registration,
    create_rapidpro_public_registration,
    get_whatsapp_contact,
    request_to_jembi_api,
    validate_subscribe_jembi_app_registration,
)

try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin


logger = logging.getLogger(__name__)


def transform_language_code(lang):
    return {
        "zu": "zul_ZA",
        "xh": "xho_ZA",
        "af": "afr_ZA",
        "en": "eng_ZA",
        "nso": "nso_ZA",
        "tn": "tsn_ZA",
        "st": "sot_ZA",
        "ts": "tso_ZA",
        "ss": "ssw_ZA",
        "ve": "ven_ZA",
        "nr": "nbl_ZA",
    }[lang]


def CursorPaginationFactory(field):
    """
    Returns a CursorPagination class with the field specified by field
    """

    class CustomCursorPagination(CursorPagination):
        ordering = field

    name = "{}CursorPagination".format(field.capitalize())
    CustomCursorPagination.__name__ = name
    CustomCursorPagination.__qualname__ = name

    return CustomCursorPagination


class IdCursorPagination(CursorPagination):
    ordering = "id"


class CreatedAtCursorPagination(CursorPagination):
    ordering = "-created_at"


class HookViewSet(viewsets.ModelViewSet):
    """
    Retrieve, create, update or destroy webhooks.
    """

    permission_classes = (IsAuthenticated,)
    queryset = Hook.objects.all()
    serializer_class = HookSerializer
    pagination_class = IdCursorPagination

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class UserViewSet(viewsets.ReadOnlyModelViewSet):

    """
    API endpoint that allows users to be viewed or edited.
    """

    permission_classes = (IsAuthenticated,)
    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = IdCursorPagination


class UserView(APIView):
    """ API endpoint that allows users creation and returns their token.
    Only admin users can do this to avoid permissions escalation.
    """

    permission_classes = (IsAdminUser,)

    def post(self, request):
        """Create a user and token, given an email. If user exists just
        provide the token."""
        serializer = CreateUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data.get("email")
        try:
            user = User.objects.get(username=email)
        except User.DoesNotExist:
            user = User.objects.create_user(email, email=email)
        token, created = Token.objects.get_or_create(user=user)

        return Response(status=status.HTTP_201_CREATED, data={"token": token.key})


class GroupViewSet(viewsets.ReadOnlyModelViewSet):

    """
    API endpoint that allows groups to be viewed or edited.
    """

    permission_classes = (IsAuthenticated,)
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    pagination_class = IdCursorPagination


class SourceViewSet(viewsets.ModelViewSet):

    """
    API endpoint that allows sources to be viewed or edited.
    """

    permission_classes = (IsAdminUser,)
    queryset = Source.objects.all()
    serializer_class = SourceSerializer
    pagination_class = IdCursorPagination


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
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class RegistrationFilter(filters.FilterSet):
    """Filter for registrations created, using ISO 8601 formatted dates"""

    created_before = django_filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="lte"
    )
    created_after = django_filters.IsoDateTimeFilter(
        field_name="created_at", lookup_expr="gte"
    )

    class Meta:
        model = Registration
        ("reg_type", "registrant_id", "validated", "source", "created_at")
        fields = [
            "reg_type",
            "registrant_id",
            "validated",
            "source",
            "created_before",
            "created_after",
        ]


class RegistrationGetViewSet(viewsets.ReadOnlyModelViewSet):
    """ API endpoint that allows Registrations to be viewed.
    """

    permission_classes = (IsAuthenticated,)
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    filterset_class = RegistrationFilter
    pagination_class = CreatedAtCursorPagination


class JembiHelpdeskOutgoingView(APIView):
    """ API endpoint that allows the helpdesk to post messages to Jembi
    """

    permission_classes = (IsAuthenticated,)
    UNCLASSIFIED_MESSAGES_DEFAULT_LABEL = "Unclassified"

    def build_jembi_helpdesk_json(self, validated_data):
        def jembi_format_date(date):
            return date.strftime("%Y%m%d%H%M%S")

        def get_software_type(channel_id):
            """ Returns the swt value based on the type of the Junebug channel.
                Defaults to sms type
            """
            if channel_id == "":
                return 2

            cache_key = "SW_TYPE_{}".format(channel_id)
            sw_type = cache.get(cache_key, None)

            if not sw_type:
                result = requests.get(
                    "%s/jb/channels/%s" % (settings.JUNEBUG_BASE_URL, channel_id),
                    headers={"Content-Type": "application/json"},
                    auth=(settings.JUNEBUG_USERNAME, settings.JUNEBUG_PASSWORD),
                )
                result.raise_for_status()
                channel_config = result.json()

                sw_type = 2
                if (
                    channel_config["result"].get("type", None)
                    == settings.WHATSAPP_CHANNEL_TYPE
                ):
                    sw_type = 4

                cache.set(cache_key, sw_type)

            return sw_type

        registration = (
            Registration.objects.filter(registrant_id=validated_data.get("user_id"))
            .order_by("-created_at")
            .first()
        )
        swt = get_software_type(validated_data.get("inbound_channel_id", ""))

        json_template = {
            "encdate": jembi_format_date(validated_data.get("inbound_created_on")),
            "repdate": jembi_format_date(validated_data.get("outbound_created_on")),
            "mha": 1,
            "swt": swt,  # 1 ussd, 2 sms, 4 whatsapp
            "cmsisdn": validated_data.get("to"),
            "dmsisdn": validated_data.get("to"),
            "faccode": registration.data.get("faccode") if registration else None,
            "data": {
                "question": validated_data.get("reply_to"),
                "answer": validated_data.get("content"),
            },
            "class": validated_data.get("label")
            or self.UNCLASSIFIED_MESSAGES_DEFAULT_LABEL,
            "type": 7,  # 7 helpdesk
            "op": str(validated_data.get("helpdesk_operator_id")),
            "eid": str(UUID(int=validated_data.get("message_id"))),
            "sid": validated_data.get("user_id"),
        }
        return json_template

    def post(self, request):
        if not (
            settings.JEMBI_BASE_URL
            and settings.JEMBI_USERNAME
            and settings.JEMBI_PASSWORD
        ):
            return Response(
                "Jembi integration is not configured properly.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = JembiHelpdeskOutgoingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post_data = self.build_jembi_helpdesk_json(serializer.validated_data)
        source = Source.objects.get(user=self.request.user.id)
        endpoint = "helpdesk"
        if source.name == "NURSE Helpdesk App":
            endpoint = "nc/helpdesk"
            post_data["type"] = 12  # NC Helpdesk
        jembi_url = urljoin(settings.JEMBI_BASE_URL, endpoint)
        request_to_jembi_api.delay(jembi_url, post_data)

        return Response(status=status.HTTP_200_OK)


class HealthcheckView(APIView):

    """ Healthcheck Interaction
        GET - returns service up - getting auth'd requires DB
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        status = 200
        resp = {"up": True, "result": {"database": "Accessible"}}
        return Response(resp, status=status)


class JembiFacilityCheckHealthcheckView(APIView):

    """ Jembi Facility Check Healthcheck Interaction
        GET - returns service up - getting auth'd requires DB
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        if not (
            settings.JEMBI_BASE_URL
            and settings.JEMBI_USERNAME
            and settings.JEMBI_PASSWORD
        ):

            return Response(
                "Jembi integration is not configured properly.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            clinic_code = request.query_params.get("clinic_code")
            result = requests.get(
                urljoin(settings.JEMBI_BASE_URL, "NCfacilityCheck"),
                headers={"Content-Type": "application/json"},
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                params={"criteria": "value:{}".format(clinic_code)},
                verify=False,
                timeout=10.0,
            )
            result.raise_for_status()

            jembi_result = result.json()

            if "rows" in jembi_result:
                resp = {"up": True}

        except (requests.exceptions.HTTPError,) as e:
            if e.response.status_code == 400:
                logger.warning(
                    "400 Error when posting to Jembi.\n"
                    "Response: Payload:%s" % (e.response.content)
                )
                return Response(
                    {"request_error": "HTTP 400 Bad Request"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                raise e

        except (requests.exceptions.Timeout,) as e:
            logger.warning(
                "504 Timeout Error when posting to Jembi.\n"
                "Response: %s\nPayload:%s" % (e.response.text)
            )
            return Response(
                "Timeout Error when posting to Jembi. Body: %s Payload: %r"
                % (e.response.content),
                status=status.HTTP_504_GATEWAY_TIMEOUT,
            )

        return Response(resp, status=status.HTTP_200_OK)


class ThirdPartyRegistration(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        is_client = IdentityStoreApiClient(
            api_url=settings.IDENTITY_STORE_URL,
            auth_token=settings.IDENTITY_STORE_TOKEN,
        )
        serializer = ThirdPartyRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            mom_msisdn = serializer.validated_data["mom_msisdn"]
            hcw_msisdn = serializer.validated_data["hcw_msisdn"]
            lang_code = serializer.validated_data["mom_lang"]
            lang_code = transform_language_code(lang_code)
            authority = serializer.validated_data["authority"]
            # load the users sources with authority mapping
            if authority == "chw":
                source_auth = "hw_partial"
            elif authority == "clinic":
                source_auth = "hw_full"
            else:
                source_auth = "patient"
            source = Source.objects.get(user=self.request.user, authority=source_auth)
            if mom_msisdn != hcw_msisdn:
                # Get or create HCW Identity
                result = list(
                    is_client.get_identity_by_address("msisdn", hcw_msisdn)["results"]
                )
                if len(result) < 1:
                    identity = {
                        "details": {
                            "default_addr_type": "msisdn",
                            "addresses": {"msisdn": {hcw_msisdn: {"default": True}}},
                        }
                    }
                    hcw_identity = is_client.create_identity(identity)
                else:
                    hcw_identity = result[0]
            else:
                hcw_identity = None

            id_type = serializer.validated_data["mom_id_type"]
            if hcw_identity is not None:
                operator = hcw_identity["id"]
                device = hcw_msisdn
            else:
                operator = None
                device = mom_msisdn

            # auth: chw, clinic,
            # Get or create Mom Identity
            result = list(
                is_client.get_identity_by_address("msisdn", mom_msisdn)["results"]
            )
            if len(result) < 1:
                identity = {
                    "details": {
                        "default_addr_type": "msisdn",
                        "addresses": {"msisdn": {mom_msisdn: {"default": True}}},
                        "operator_id": operator,
                        "lang_code": lang_code,
                        "id_type": id_type,
                        "mom_dob": serializer.validated_data["mom_dob"],
                        "last_edd": serializer.validated_data["mom_edd"],
                        "faccode": serializer.validated_data["clinic_code"],
                        "consent": serializer.validated_data["consent"],
                        "last_mc_reg_on": authority,
                        "source": "external",
                    }
                }
                if id_type == "sa_id":
                    identity["details"]["sa_id_no"] = serializer.validated_data[
                        "mom_id_no"
                    ]
                elif id_type == "passport":
                    identity["details"]["passport_origin"] = serializer.validated_data[
                        "mom_passport_origin"
                    ]
                    identity["details"]["passport_no"] = serializer.validated_data[
                        "mom_id_no"
                    ]
                mom_identity = is_client.create_identity(identity)
            else:
                mom_identity = result[0]
                # Update Seed Identity record
                details = mom_identity["details"]
                details["operator_id"] = operator
                details["lang_code"] = lang_code
                details["id_type"] = id_type
                details["mom_dob"] = serializer.validated_data["mom_dob"]
                details["last_edd"] = serializer.validated_data["mom_edd"]
                details["faccode"] = serializer.validated_data["clinic_code"]
                details["consent"] = serializer.validated_data["consent"]
                details["last_mc_reg_on"] = authority
                details["source"] = "external"
                if id_type == "sa_id":
                    details["sa_id_no"] = serializer.validated_data["mom_id_no"]
                elif id_type == "passport":
                    details["passport_origin"] = serializer.validated_data[
                        "mom_passport_origin"
                    ]
                    details["passport_no"] = serializer.validated_data["mom_id_no"]
                mom_identity["details"] = details
                result = is_client.update_identity(
                    mom_identity["id"], data=mom_identity
                )
                # update_identity returns the object directly as JSON
                mom_identity = result

            # Create registration
            reg_data = {
                "operator_id": operator,
                "msisdn_registrant": mom_msisdn,
                "msisdn_device": device,
                "id_type": id_type,
                "language": lang_code,
                "mom_dob": serializer.validated_data["mom_dob"],
                "edd": serializer.validated_data["mom_edd"],
                "faccode": serializer.validated_data["clinic_code"],
                "consent": serializer.validated_data["consent"],
                "mha": serializer.validated_data.get("mha", 1),
                "swt": serializer.validated_data.get("swt", 1),
            }
            if "encdate" in serializer.validated_data:
                reg_data["encdate"] = serializer.validated_data["encdate"]
            if id_type == "sa_id":
                reg_data["sa_id_no"] = serializer.validated_data["mom_id_no"]
            elif id_type == "passport":
                reg_data["passport_origin"] = serializer.validated_data[
                    "mom_passport_origin"
                ]
                reg_data["passport_no"] = serializer.validated_data["mom_id_no"]
            reg = Registration.objects.create(
                reg_type="momconnect_prebirth",
                registrant_id=mom_identity["id"],
                source=source,
                data=reg_data,
                created_by=self.request.user,
                updated_by=self.request.user,
            )
            reg_serializer = RegistrationSerializer(instance=reg)
            return Response(reg_serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class JembiAppRegistration(generics.CreateAPIView):
    """
    MomConnect prebirth registrations from the Jembi App
    """

    permission_classes = (IsAuthenticated,)
    serializer_class = JembiAppRegistrationSerializer

    @classmethod
    def create_registration(cls, user: User, data: dict) -> Tuple[int, dict]:
        source = Source.objects.get(user=user)
        serializer = cls.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)

        created = serializer.validated_data.pop("created")
        external_id = serializer.validated_data.pop("external_id", None) or None

        # We encode and decode from JSON to ensure dates are encoded properly
        data = json.loads(JSONEncoder().encode(serializer.validated_data))

        try:
            registration = Registration.objects.create(
                external_id=external_id,
                reg_type="jembi_momconnect",
                registrant_id=None,
                data=data,
                source=source,
                created_by=user,
            )
        except IntegrityError:
            return (
                status.HTTP_400_BAD_REQUEST,
                {"external_id": ["This field must be unique."]},
            )

        # Overwrite the created_at date with the one provided
        registration.created_at = created
        registration.save()

        validate_subscribe_jembi_app_registration.delay(
            registration_id=str(registration.pk)
        )

        return status.HTTP_202_ACCEPTED, RegistrationSerializer(registration).data

    def post(self, request: Request) -> Response:
        status, response = self.create_registration(request.user, request.data)
        return Response(response, status=status)


class JembiAppRegistrationStatus(APIView):
    """
    Status of registrations
    """

    permission_classes = (IsAuthenticated,)

    @classmethod
    def get_registration(cls, user: User, reg_id: str) -> Registration:
        try:
            reg = Registration.objects.get(external_id=reg_id)
        except Registration.DoesNotExist:
            try:
                reg = get_object_or_404(Registration, id=reg_id)
            except ValidationError:
                raise Http404()

        if reg.created_by_id != user.id:
            raise PermissionDenied()
        return reg

    def get(self, request: Request, registration_id: str) -> Response:
        registration = self.get_registration(request.user, registration_id)
        return Response(registration.status, status=status.HTTP_200_OK)


class MetricsView(APIView):

    """ Metrics Interaction
        GET - returns list of all available metrics on the service
        POST - starts up the task that fires all the scheduled metrics
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        status = 200
        resp = {"metrics_available": get_available_metrics()}
        return Response(resp, status=status)

    def post(self, request, *args, **kwargs):
        status = 201
        # Uncomment line below if scheduled metrics are added
        # scheduled_metrics.apply_async()
        resp = {"scheduled_metrics_initiated": True}
        return Response(resp, status=status)


class IncrementPositionPermission(DjangoModelPermissions):
    """
    Allows POST requests if the user has the increment_position permission
    """

    perms_map = {"POST": ["%(app_label)s.increment_position_%(model_name)s"]}


class PositionTrackerViewset(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):

    permission_classes = (DjangoModelPermissions,)
    queryset = PositionTracker.objects.all()
    serializer_class = PositionTrackerSerializer
    pagination_class = CursorPaginationFactory("label")

    @action(
        detail=True, methods=["post"], permission_classes=[IncrementPositionPermission]
    )
    def increment_position(self, request, pk=None):
        """
        Increments the position on the specified position tracker. Only allows
        an update once every 12 hours to avoid retried HTTP requests
        incrementing the position more than once
        """
        position_tracker = self.get_object()

        time_difference = timezone.now() - position_tracker.modified_at
        if time_difference < datetime.timedelta(hours=12):
            return Response(
                {
                    "error": "The position may only be incremented once every 12 "
                    "hours"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        position_tracker.position += 1
        position_tracker.save(update_fields=("position",))

        serializer = self.get_serializer(instance=position_tracker)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EngageBaseView(object):
    """
    A base view for shared functionality between Engage views
    """

    def validate_signature(self, request):
        secret = settings.ENGAGE_CONTEXT_HMAC_SECRET
        try:
            signature = request.META["HTTP_X_ENGAGE_HOOK_SIGNATURE"]
        except KeyError:
            raise AuthenticationFailed("X-Engage-Hook-Signature header required")

        h = hmac.new(secret.encode(), request.body, sha256)

        if not hmac.compare_digest(base64.b64encode(h.digest()).decode(), signature):
            raise AuthenticationFailed("Invalid hook signature")


class EngageContextView(EngageBaseView, generics.CreateAPIView):
    serializer_class = EngageContextSerializer

    # Since these external requests are happening in the request loop, we need to
    # ensure that they are quick
    identity_store = IdentityStoreApiClient(
        api_url=settings.IDENTITY_STORE_URL,
        auth_token=settings.IDENTITY_STORE_TOKEN,
        retries=0,
        timeout=1,
    )
    stage_based_messaging = StageBasedMessagingApiClient(
        api_url=settings.STAGE_BASED_MESSAGING_URL,
        auth_token=settings.STAGE_BASED_MESSAGING_TOKEN,
        retries=0,
        timeout=1,
    )

    LOOKUP_FIELDS = (
        ("faccode", "Facility Code"),
        ("edd", "Expected Due Date"),
        ("mom_dob", "Date of Birth"),
    )

    def get_msisdn(self, data):
        """
        Gets the MSISDN of the user, if present in the request, otherwise returns None
        """
        return data["chat"]["owner"]

    def get_identity(self, msisdn):
        """
        Gets the identity for the msisdn, if exists, otherwise returns None
        """
        try:
            identity = self.identity_store.get_identity_by_address("msisdn", msisdn)
            return next(identity["results"])
        # Catch both no results and HTTP errors
        except (StopIteration, RequestException):
            return None

    def get_registrations(self, identity):
        """
        Gets the list of registrations for the identity, ordered from oldest to newest.
        If there is no identity, returns empty list
        """
        try:
            identity_id = identity["id"]
        except (KeyError, TypeError):
            return []

        return Registration.objects.filter(registrant_id=identity_id).order_by(
            "created_at"
        )

    def lookup_field_from_dictionaries(self, field, *dictionaries):
        """
        Given a field and one or more dictionaries, returns the first match that it
        finds, or None if no match is found
        """
        for dictionary in dictionaries:
            if field in dictionary:
                return dictionary[field]

    def get_subscriptions(self, identity):
        """
        Gets the list of active subscription labels for the given identity. If there
        is no identity, returns an empty list
        """
        try:
            identity_id = identity["id"]
        except (KeyError, TypeError):
            return []

        try:
            subscriptions = self.stage_based_messaging.get_subscriptions(
                {"identity": identity_id, "active": True}
            )
            return [sub["messageset_label"] for sub in subscriptions["results"]]
        except RequestException:
            # Catch HTTP errors and fail in a clean way
            return []

    def extract_registration_info(self, identity, registrations):
        """
        Extracts the info from the identity and registrations to be displayed.
        Returns a map of labels and values.
        """
        result = {}

        registrations_details = []
        for registration in registrations:
            result["Registration Type"] = registration.get_reg_type_display()
            registrations_details.append(registration.data)

        # Reverse registration details so that we get latest information first
        registrations_details = registrations_details[::-1]

        try:
            identity_details = identity["details"]
        except (KeyError, TypeError):
            identity_details = {}

        for field, label in self.LOOKUP_FIELDS:
            value = self.lookup_field_from_dictionaries(
                field, identity_details, *registrations_details
            )
            if value:
                result[label] = value

        return result

    def generate_actions(self, identity, subscriptions):
        """
        Returns an object describing the list of available actions
        """
        actions = {}

        try:
            identity_id = identity["id"]
        except (KeyError, TypeError):
            return actions

        if any("pregnancy" in sub.lower() for sub in subscriptions):
            actions["baby_switch"] = {
                "description": "Switch to baby messaging",
                "url": reverse("engage-action"),
                "payload": {
                    "registrant_id": identity_id,
                    "action": "baby_switch",
                    "data": {},
                },
            }

        if any("whatsapp" in sub.lower() for sub in subscriptions):
            actions["switch_to_sms"] = {
                "description": "Switch channel to SMS",
                "url": reverse("engage-action"),
                "payload": {
                    "registrant_id": identity_id,
                    "action": "switch_channel",
                    "data": {"channel": "sms"},
                },
            }
        else:
            actions["switch_to_whatsapp"] = {
                "description": "Switch channel to WhatsApp",
                "url": reverse("engage-action"),
                "payload": {
                    "registrant_id": identity_id,
                    "action": "switch_channel",
                    "data": {"channel": "whatsapp"},
                },
            }

        actions["opt_out"] = {
            "description": "Opt out",
            "url": reverse("engage-action"),
            "payload": {
                "registrant_id": identity_id,
                "action": "momconnect_loss_optout",
            },
            "options": {
                "miscarriage": "Miscarriage",
                "stillbirth": "Baby was stillborn",
                "babyloss": "Baby died",
                "not_useful": "Messages not useful",
                "other": "Other",
                "unknown": "Unknown",
            },
        }

        actions["switch_to_loss"] = {
            "description": "Switch to loss messaging",
            "url": reverse("engage-action"),
            "payload": {
                "registrant_id": identity_id,
                "action": "momconnect_loss_switch",
            },
            "options": {
                "miscarriage": "Miscarriage",
                "stillbirth": "Baby was stillborn",
                "babyloss": "Baby died",
            },
        }

        actions["switch_language"] = {
            "description": "Change language",
            "url": reverse("engage-action"),
            "payload": {
                "registrant_id": identity_id,
                "action": "momconnect_change_language",
            },
            "options": {
                "zul_ZA": "isiZulu",
                "xho_ZA": "isiXhosa",
                "afr_ZA": "Afrikaans",
                "eng_ZA": "English",
                "nso_ZA": "Sesotho sa Leboa / Sepedi",
                "tsn_ZA": "Setswana",
                "sot_ZA": "Sesotho",
                "tso_ZA": "Xitsonga",
                "ssw_ZA": "siSwati",
                "ven_ZA": "Tshivenda",
                "nbl_ZA": "isiNdebele",
            },
        }

        return actions

    def post(self, request):
        self.validate_signature(request)

        if "handshake" in request.data:
            resp = {
                "capabilities": {
                    "actions": True,
                    "context_objects": [
                        {
                            "title": "Mother's Details",
                            "code": "mother_details",
                            "icon": "info-circle",
                            "type": "table",
                        },
                        {
                            "title": "Subscriptions",
                            "code": "subscriptions",
                            "icon": "profile",
                            "type": "ordered-list",
                        },
                    ],
                }
            }
            return Response(resp, status=status.HTTP_200_OK)

        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)

        context = {"mother_details": {}, "subscriptions": []}

        msisdn = self.get_msisdn(serializer.validated_data)
        identity = self.get_identity(msisdn)
        registrations = self.get_registrations(identity)
        info = self.extract_registration_info(identity, registrations)
        if info:
            context["mother_details"] = info

        subscriptions = self.get_subscriptions(identity)
        if subscriptions:
            context["subscriptions"] = subscriptions

        return Response(
            {
                "version": "1.0.0-alpha",
                "context_objects": context,
                "actions": self.generate_actions(identity, subscriptions),
            }
        )


class EngageActionView(EngageBaseView, generics.CreateAPIView):
    serializer_class = EngageActionSerializer

    def post(self, request):
        self.validate_signature(request)

        serializer = self.get_serializer(data=request.data)
        option = request.data.pop("option", None)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        change_data = data["payload"]
        change_data["created_by"] = change_data["updated_by"] = request.user
        change_data["source"] = Source.objects.get(user=self.request.user)

        if change_data.get("action") == "momconnect_loss_optout":
            change_data["data"] = {"reason": option}
            if option in ["not_useful", "other", "unknown"]:
                change_data["action"] = "momconnect_nonloss_optout"
        if change_data.get("action") == "momconnect_loss_switch":
            change_data["data"] = {"reason": option}
        if change_data.get("action") == "momconnect_change_language":
            change_data["data"] = {"language": option}

        change_data["data"]["engage"] = {
            "integration_uuid": data["integration_uuid"],
            "integration_action_uuid": data["integration_action_uuid"],
        }

        change = Change.objects.create(**change_data)

        return Response(ChangeSerializer(change).data, status=status.HTTP_201_CREATED)


class BearerTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"


class PruneContactsPermission(DjangoModelPermissions):
    """
    Allows POST requests if the user has the can_prune_contacts permission
    """

    perms_map = {"POST": ["%(app_label)s.can_prune_%(model_name)s"]}


class WhatsAppContactCheckViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    authentication_classes = (SessionAuthentication, BearerTokenAuthentication)
    permission_classes = (DjangoModelPermissions,)
    serializer_class = WhatsAppContactCheckSerializer
    queryset = WhatsAppContact.objects.all()

    def get_status(self, blocking, msisdn):
        msisdn = msisdn.raw_input
        try:
            contact = WhatsAppContact.objects.get(msisdn=msisdn)
            return contact.api_format
        except WhatsAppContact.DoesNotExist:
            if blocking == "wait":
                # Default to the contact not existing
                return {"input": msisdn, "status": "invalid"}
            else:
                get_whatsapp_contact.delay(msisdn=msisdn)
                return {"input": msisdn, "status": "processing"}

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        results = map(partial(self.get_status, data["blocking"]), data["contacts"])
        return Response({"contacts": results}, status=status.HTTP_201_CREATED)

    @action(
        detail=False, methods=["post"], permission_classes=[PruneContactsPermission]
    )
    def prune(self, request):
        """
        Prunes any contacts older than 7 days in the database
        """
        WhatsAppContact.objects.filter(
            created__lt=timezone.now() - datetime.timedelta(days=7)
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FacilityCodeCheckView(APIView):
    """ Facility Code Check
        GET - returns clinic name and clinic code for varification
        getting auth'd requires DB
    """

    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        if not (
            settings.JEMBI_BASE_URL
            and settings.JEMBI_USERNAME
            and settings.JEMBI_PASSWORD
        ):
            return Response(
                "Jembi integration is not configured properly.",
                status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            clinic_code = request.query_params.get("clinic_code")
            result = requests.get(
                urljoin(settings.JEMBI_BASE_URL, "facilityCheck"),
                headers={"Content-Type": "application/json"},
                auth=(settings.JEMBI_USERNAME, settings.JEMBI_PASSWORD),
                params={"criteria": "value:{}".format(clinic_code)},
                verify=False,
            )
            result.raise_for_status()
            jembi_result = result.json()
            if len(jembi_result.get("rows")) > 0:
                facility = jembi_result.get("rows")[0][3]
                resp = {"Facility": facility}
            else:
                resp = {"Facility": "invalid"}

        except (requests.exceptions.HTTPError,) as e:
            if e.response.status_code == 400:
                logger.warning(
                    "400 Error when posting to Jembi.\n"
                    "Response: %s\nPayload:" % (e.response.text)
                )
                return Response(
                    "Error when posting to Jembi. Body: %s" % (e.response.content),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                raise e

        return Response(resp, status=status.HTTP_200_OK)


class ServiceUnavailable(APIException):
    status_code = 503
    default_detail = "Service temporarily unavailable, try again later."
    default_code = "service_unavailable"


class SubscriptionCheckPermission(DjangoModelPermissions):
    """
    Allows GET requests if the user has the subscription_check permission
    """

    perms_map = {"GET": ["%(app_label)s.subscription_check_%(model_name)s"]}


class SubscriptionCheckView(APIView):
    queryset = Registration.objects.none()  # For DjangoModelPermissions
    permission_classes = (SubscriptionCheckPermission,)

    def get_msisdn(self, data):
        return phonenumbers.format_number(
            data["msisdn"], phonenumbers.PhoneNumberFormat.E164
        )

    def get_identity(self, msisdn):
        try:
            return next(is_client.get_identity_by_address("msisdn", msisdn)["results"])
        except StopIteration:
            return None
        except (RequestException, HTTPServiceError):
            raise ServiceUnavailable()

    def _get_messagesets(self):
        try:
            return {
                ms["id"]: ms["short_name"]
                for ms in sbm_client.get_messagesets()["results"]
            }
        except (RequestException, HTTPServiceError):
            raise ServiceUnavailable()

    def get_messagesets(self):
        return cache.get_or_set("messagesets", self._get_messagesets, 300)

    def get_subscriptions(self, identity_id):
        messagesets = self.get_messagesets()
        try:
            subscriptions = sbm_client.get_subscriptions(
                {"identity": identity_id, "active": True}
            )["results"]
            return [messagesets[s["messageset"]] for s in subscriptions]
        except (RequestException, HTTPServiceError):
            raise ServiceUnavailable()

    def get_subscription_description(self, identity_id: str) -> str:
        """
        Gets a human readable string of the details of the current subscriptions
        """
        try:
            last_optout = Change.objects.filter(
                registrant_id=identity_id,
                action__in=(
                    "baby_switch",
                    "pmtct_loss_switch",
                    "pmtct_loss_optout",
                    "pmtct_nonloss_optout",
                    "momconnect_loss_switch",
                    "momconnect_loss_optout",
                    "momconnect_nonloss_optout",
                ),
                validated=True,
            ).latest("created_at")
            last_optout = last_optout.created_at
        except Change.DoesNotExist:
            last_optout = timezone.utc.localize(datetime.datetime.min)
        try:
            last_baby_switch = Change.objects.filter(
                registrant_id=identity_id, action="baby_switch", validated=True
            ).latest("created_at")
            last_baby_switch = last_baby_switch.created_at
        except Change.DoesNotExist:
            last_baby_switch = timezone.utc.localize(datetime.datetime.min)

        registrations = Registration.objects.filter(
            registrant_id=identity_id,
            reg_type__in=(
                "momconnect_prebirth",
                "momconnect_postbirth",
                "whatsapp_prebirth",
                "whatsapp_postbirth",
            ),
            created_at__gte=max((last_optout, last_baby_switch)),
            validated=True,
        )
        changes = Change.objects.filter(
            registrant_id=identity_id,
            action="baby_switch",
            created_at__gte=last_optout,
            validated=True,
        )
        subscriptions = []
        for registration in registrations:
            try:
                edd = datetime.datetime.strptime(
                    registration.data["edd"], "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
                if edd < timezone.now():
                    # Messaging continues for 2 weeks after edd before being switched
                    edd += datetime.timedelta(weeks=2)
                subscriptions.append(edd)
            except KeyError:
                pass
            try:
                baby_dob = datetime.datetime.strptime(
                    registration.data["baby_dob"], "%Y-%m-%d"
                ).replace(tzinfo=timezone.utc)
                subscriptions.append(baby_dob)
            except KeyError:
                pass
        for change in changes:
            subscriptions.append(change.created_at)
        subscriptions.sort()
        # Filter out expired subscriptions
        subs = filter(
            lambda s: s > timezone.now() - datetime.timedelta(weeks=37 + 104),
            subscriptions,
        )
        texts = map(lambda s: "baby born on {:%Y-%m-%d}".format(s), subs)
        return ", ".join(texts)

    def derive_subscription_status(self, subscriptions):
        for subscription in subscriptions:
            if "momconnect_prebirth.hw_full" in subscription:
                return "clinic"
            if (
                "momconnect_prebirth.hw_partial" in subscription
                or "momconnect_prebirth.patient" in subscription
            ):
                return "public"
            if "momconnect_postbirth.hw_full" in subscription:
                return "postbirth"
        return "none"

    def derive_optout_status(self, identity, msisdn):
        return (
            identity.get("details", {})
            .get("addresses", {})
            .get("msisdn", {})
            .get(msisdn, {})
            .get("optedout", False)
        )

    def get(self, request):
        serializer = SubscriptionsCheckSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        msisdn = self.get_msisdn(serializer.validated_data)
        identity = self.get_identity(msisdn)
        if identity is None:
            return Response({"subscription_status": "none", "opted_out": False})
        subscriptions = self.get_subscriptions(identity["id"])
        subscription_status = self.derive_subscription_status(subscriptions)
        opted_out = self.derive_optout_status(identity, msisdn)
        subscription_description = self.get_subscription_description(identity["id"])
        return Response(
            {
                "subscription_status": subscription_status,
                "opted_out": opted_out,
                "subscription_description": subscription_description,
            }
        )


class RapidProClinicRegistrationView(generics.CreateAPIView):
    queryset = Registration.objects.none()
    permission_classes = (DjangoModelPermissions,)
    serializer_class = BaseRapidProClinicRegistrationSerializer

    def get_regtype_serializer_class(self, reg_type: str) -> Serializer:
        return {
            "prebirth": PrebirthRapidProClinicRegistrationSerializer,
            "postbirth": PostBirthRapidProClinicRegistrationSerializer,
        }[reg_type]

    def get_idtype_serializer_class(self, id_type: str) -> Serializer:
        return {
            "sa_id": SaIdNoRapidProClinicRegistrationSerializer,
            "passport": PassportRapidProClinicRegistrationSerializer,
            "none": DoBRapidProClinicRegistrationSerializer,
        }[id_type]

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer_class()(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data["user_id"] = request.user.id

        regtype_serializer = self.get_regtype_serializer_class(
            data["registration_type"]
        )(data=request.query_params)
        regtype_serializer.is_valid(raise_exception=True)
        data.update(regtype_serializer.validated_data)

        idtype_serializer = self.get_idtype_serializer_class(data["mom_id_type"])(
            data=request.query_params
        )
        idtype_serializer.is_valid(raise_exception=True)
        data.update(idtype_serializer.validated_data)

        # Serialize the dates
        for field in ("mom_dob", "mom_edd", "baby_dob"):
            if data.get(field):
                data[field] = data[field].strftime("%Y-%m-%d")
        data["created"] = data["created"].isoformat()

        create_rapidpro_clinic_registration.delay(data)

        return Response(data, status=status.HTTP_202_ACCEPTED)


class RapidProPublicRegistrationView(generics.CreateAPIView):
    queryset = Registration.objects.none()
    permission_classes = (DjangoModelPermissions,)
    serializer_class = RapidProPublicRegistrationSerializer

    def post(self, request: Request) -> Response:
        serializer = self.get_serializer_class()(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        data["user_id"] = request.user.id

        # Serialize the dates
        data["created"] = data["created"].isoformat()

        create_rapidpro_public_registration.delay(data)

        return Response(data, status=status.HTTP_202_ACCEPTED)
