import json

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from registrations.models import ClinicCode


class FacilityCheckViewTests(APITestCase):
    def test_filter_by_code(self):
        ClinicCode.objects.create(
            code="123456", value="123456", uid="cc1", name="test1"
        )
        ClinicCode.objects.create(
            code="654321", value="123456", uid="cc2", name="test2"
        )
        user = User.objects.create_user("test", "test")
        self.client.force_authenticate(user)

        url = reverse("facility-check")
        r = self.client.get(url, {"criteria": "code:123456"})
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertEqual(
            json.loads(r.content),
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
                "rows": [["123456", "123456", "cc1", "test1"]],
                "width": 4,
                "height": 1,
            },
        )
