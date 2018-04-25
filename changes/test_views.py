from django.contrib.auth.models import User, Permission
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest import mock

from rest_framework.test import APITestCase


@mock.patch('changes.views.tasks.process_whatsapp_unsent_event')
class ReceiveWhatsAppEventViewTests(APITestCase):
    def test_no_auth(self, task):
        """
        If there is no or invalid auth supplied, a 401 error should be returned
        """
        url = reverse('whatsapp_event')

        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        url = '{}?token=badtoken'.format(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_querystring_auth_token(self, task):
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

    def test_permission_required(self, task):
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

    def test_serializer_failed(self, task):
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

    def test_serializer_succeeded(self, task):
        """
        If the serializer passes, then the task should be called with the
        correct parameters
        """
        user = User.objects.create_user('test')
        user.user_permissions.add(
            Permission.objects.get(codename='add_change'))
        self.client.force_authenticate(user=user)
        url = reverse('whatsapp_event')

        response = self.client.post(url, {
            'hook': {
                'event': 'message.direct_outbound.status',
            },
            'data': {
                'message_metadata': {
                    'junebug_message_id': '41c377a47b064eba9abee5a1ea827b3d',
                },
                'status': 'unsent',
            },
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task.delay.assert_called_once_with(
            '41c377a47b064eba9abee5a1ea827b3d', user.pk)
