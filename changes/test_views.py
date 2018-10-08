import json
from django.contrib.auth.models import User, Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest import mock
from urllib.parse import urlencode

from rest_framework.test import APITestCase


@mock.patch('changes.views.ReceiveWhatsAppBase.validate_signature')
@mock.patch('changes.views.tasks.process_whatsapp_unsent_event')
class ReceiveWhatsAppEventViewTests(APITestCase):
    def test_no_auth(self, task, mock_validate_signature):
        """
        If there is no or invalid auth supplied, a 401 error should be returned
        """
        url = reverse('whatsapp_event')

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        url = '{}?token=badtoken'.format(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_querystring_auth_token(self, task, mock_validate_signature):
        """
        The token should be able to be specified in the query string
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        token = Token.objects.create(user=user)
        url = '{}?token={}'.format(
            reverse('whatsapp_event'), str(token.key))

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_permission_required(self, task, mock_validate_signature):
        """
        The authenticated user must have permission to create a Change
        """
        user = User.objects.create_user('test')
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_event')

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        user = User.objects.get(pk=user.pk)
        self.client.force_authenticate(user=user)

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_serializer_failed(self, task, mock_validate_signature):
        """
        If the serializer doesn't pass, then a 204 should be returned, and the
        task shouldn't be called
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_event')

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(task.called)

    def test_serializer_succeeded(self, task, mock_validate_signature):
        """
        If the serializer passes, then the task should be called with the
        correct parameters
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_event')

        errors = [
            {"code": 500, "title": "structure unavailable: Client could not display highly structured message"}  # noqa
        ]

        response = self.client.post(url, {
            "statuses": [
                {
                    "errors": errors,
                    "id": "41c377a47b064eba9abee5a1ea827b3d",
                    "recipient_id": "27831112222",
                    "status": "failed",
                    "timestamp": "1538388353"
                }
            ]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task.delay.assert_called_once_with(
            '41c377a47b064eba9abee5a1ea827b3d', user.pk, errors)


@mock.patch('changes.views.ReceiveWhatsAppBase.validate_signature')
@mock.patch('changes.views.tasks.process_whatsapp_system_event')
class ReceiveWhatsAppSystemEventViewTests(APITestCase):
    def test_serializer_succeeded(self, task, mock_validate_signature):
        """
        If the serializer passes, then the task should be called with the
        correct parameters
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_system_event')

        response = self.client.post(url, {
            "events": [{
                "recipient_id": "278311155555",
                "timestamp": "1538388353",
                "message_id": "gBGGJ4NjeFMfAgl58_8Il_tnCNI",
                "type": "undelivered"
            }]
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task.delay.assert_called_once_with('gBGGJ4NjeFMfAgl58_8Il_tnCNI',
                                           "undelivered")

    def test_serializer_failed(self, task, mock_validate_signature):
        """
        If the serializer doesn't pass, then a 400 should be returned, and the
        task shouldn't be called
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_system_event')

        response = self.client.post(url, {
            "events": [{
                "recipient_id": "278311155555",
                "timestamp": "1538388353",
                "type": "undelivered"
            }]
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(task.called)


@mock.patch('changes.views.tasks.process_whatsapp_unsent_event')
class ValidateSignatureTests(APITestCase):
    def test_no_hvac_header(self, task):
        """
        If there is no X-Engage-Hook-Signature, auth error should be raised
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_event')

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "X-Engage-Hook-Signature header required")

    def test_invalid_hvac_header(self, task):
        """
        If there is a invalid X-Engage-Hook-Signature, auth error should be
        raised
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_event')

        header = {'X-Engage-Hook-Signature': 'SECRET'}

        response = self.client.post(url, data={}, headers=header)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            json.loads(response.content)["detail"],
            "Invalid hook signature")

    def test_valid_hvac_header(self, task):
        """
        If there is a valid X-Engage-Hook-Signature, no auth error should be
        raised
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_event')

        header = {'X-Engage-Hook-Signature':
                  'Gu7dfV2kfjbT6PJ/J7N7xi4/d+y91Ys9ISMxQRxhac8='}

        errors = [
            {"code": 500, "title": "structure unavailable: Client could not display highly structured message"}  # noqa
        ]

        response = self.client.post(url, data={
            "statuses": [
                {
                    "errors": errors,
                    "id": "41c377a47b064eba9abee5a1ea827b3d",
                    "recipient_id": "27831112222",
                    "status": "failed",
                    "timestamp": "1538388353"
                }
            ]
        }, format="json", headers=header)

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task.delay.assert_called_once_with(
            '41c377a47b064eba9abee5a1ea827b3d', user.pk, errors)


class ReceiveSeedMessageSenderHookViewTests(APITestCase):
    def test_token_querystring_auth(self):
        """
        The token should be required in the querystring for requests to be
        processed.
        """
        url = reverse('message_sender_webhook')
        response = self.client.post(url, data={}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @mock.patch('changes.views.tasks.process_whatsapp_contact_check_fail')
    def test_whatsapp_contact_check_failure(self, task):
        """
        If the message sender sends us an event for whatsapp contact check fail
        then we should run the processing task.
        """
        user = User.objects.create_user("test")
        token = Token.objects.create(user=user).key
        url = "{}?{}".format(reverse('message_sender_webhook'), urlencode({
            "token": token
        }))

        response = self.client.post(url, data={
            "hook": {
                "id": 1,
                "event": "whatsapp.failed_contact_check",
                "target": "http://example.org",
            },
            "data": {
                "address": "+27820001001",
            },
        }, format="json")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task.delay.assert_called_once_with(str(user.pk), "+27820001001")
