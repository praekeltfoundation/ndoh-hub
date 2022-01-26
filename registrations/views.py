import datetime
from functools import partial

from django.utils import timezone
from rest_framework import generics, mixins, status, viewsets
from rest_framework.authentication import (
    BasicAuthentication,
    SessionAuthentication,
    TokenAuthentication,
)
from rest_framework.decorators import action
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.request import Request
from rest_framework.response import Response

from .models import ClinicCode, WhatsAppContact
from .serializers import WhatsAppContactCheckSerializer
from .tasks import get_whatsapp_contact


class BearerTokenAuthentication(TokenAuthentication):
    keyword = "Bearer"


class PruneContactsPermission(DjangoModelPermissions):
    """
    Allows POST requests if the user has the can_prune_contacts permission
    """

    perms_map = {"POST": ["%(app_label)s.can_prune_%(model_name)s"]}


class FacilityCheckView(generics.RetrieveAPIView):
    queryset = ClinicCode.objects.all()
    permission_classes = (DjangoModelPermissions,)
    authentication_classes = (BasicAuthentication,)

    def get(self, request: Request) -> Response:
        try:
            field, value = request.query_params["criteria"].split(":")
        except KeyError:
            return Response(
                {"error": "Must supply 'criteria' query parameter"},
                status.HTTP_400_BAD_REQUEST,
            )
        except ValueError:
            return Response(
                {"error": "Criteria query parameter must be in 'field:value' format"},
                status.HTTP_400_BAD_REQUEST,
            )

        results = ClinicCode.objects.filter(**{field: value}).values_list(
            "code", "value", "uid", "name"
        )
        return Response(
            {
                "title": "FacilityCheck",
                "headers": [
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "code",
                        "column": "code",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "value",
                        "column": "value",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "uid",
                        "column": "uid",
                        "type": "java.lang.String",
                    },
                    {
                        "hidden": False,
                        "meta": False,
                        "name": "name",
                        "column": "name",
                        "type": "java.lang.String",
                    },
                ],
                "rows": results,
                "width": 4,
                "height": len(results),
            }
        )


class WhatsAppContactCheckViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    authentication_classes = (SessionAuthentication, BearerTokenAuthentication)
    permission_classes = (DjangoModelPermissions,)
    serializer_class = WhatsAppContactCheckSerializer
    queryset = WhatsAppContact.objects.all()

    def get_status(self, blocking, msisdn):
        msisdn = msisdn.raw_input
        try:
            contact = WhatsAppContact.objects.filter(
                created__gt=timezone.now() - datetime.timedelta(days=7), msisdn=msisdn
            ).latest("created")
            return contact.api_format
        except WhatsAppContact.DoesNotExist:
            if blocking == "wait":
                # We'll have to do this request in-process, since we have no choice
                return get_whatsapp_contact(msisdn=msisdn)
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
