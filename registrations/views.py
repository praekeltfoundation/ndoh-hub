from rest_framework import generics, status
from rest_framework.authentication import BasicAuthentication
from rest_framework.permissions import DjangoModelPermissions
from rest_framework.request import Request
from rest_framework.response import Response


from .models import ClinicCode


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
