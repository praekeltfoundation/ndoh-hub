from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase

from changes.models import Change
from registrations.models import Source


class ChangeTests(TestCase):
    def test_is_engage_action(self):
        """
        Should return True if the Change is from an engage action, and false otherwise.
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)
        change = Change.objects.create(
            registrant_id="test-registrant-id",
            action="switch_channel",
            data={},
            source=source,
        )
        self.assertFalse(change.is_engage_action)

        change.data = {
            "engage": {
                "integration_uuid": "8cf3d402-7b25-47fd-8ef2-3e2537fccc14",
                "integration_action_uuid": "009d3a39-326c-42f3-af72-b5ddbece219a",
            }
        }
        change.save()
        self.assertTrue(change.is_engage_action)

    @mock.patch("changes.tasks.refresh_engage_context")
    def test_async_refresh_engage_context(self, task):
        """
        Asynchronously calls the task with the correct arguments
        """
        user = User.objects.create_user("test")
        source = Source.objects.create(user=user)
        change = Change.objects.create(
            registrant_id="test-registrant-id",
            action="switch_channel",
            data={
                "engage": {
                    "integration_uuid": "8cf3d402-7b25-47fd-8ef2-3e2537fccc14",
                    "integration_action_uuid": "009d3a39-326c-42f3-af72-b5ddbece219a",
                }
            },
            source=source,
        )
        change.async_refresh_engage_context()
        task.delay.assert_called_once_with(
            "8cf3d402-7b25-47fd-8ef2-3e2537fccc14",
            "009d3a39-326c-42f3-af72-b5ddbece219a",
        )
