from channels.generic.websocket import JsonWebsocketConsumer
from django.core.exceptions import PermissionDenied
from django.http import Http404
from rest_framework.exceptions import ValidationError

from registrations.views import (
    JembiAppRegistration, JembiAppRegistrationStatus)


class JembiAppRegistrationConsumer(JsonWebsocketConsumer):
    def connect(self) -> None:
        self.user = self.scope['user']
        if self.user and self.user.is_authenticated:
            self.accept()
        else:
            self.close()

    def action_registration(self, data: dict) -> None:
        """
        Attempts to create a new registration, and returns the result of the
        new registration
        """
        try:
            JembiAppRegistration.create_registration(
                self.user, data)
        except ValidationError as e:
            self.send_json({
                'registration_id': data.get('external_id'),
                'registration_data': data,
                'status': 'validation_failed',
                'error': e.detail,
            })

    def action_status(self, data: dict) -> None:
        """
        If allowed, and if it exists, attempts to get the status of a
        registration
        """
        reg_id = data.get('id', None)
        if reg_id is None:
            self.send_json({
                'registration_id': None,
                'registration_data': data,
                'status': 'validation_failed',
                'error': {
                    'id': "id must be supplied for status query",
                },
            })
            return

        try:
            reg = JembiAppRegistrationStatus.get_registration(
                self.user, reg_id)
            self.send_json(reg.status)
        except Http404:
            self.send_json({
                'registration_id': reg_id,
                'registration_data': data,
                'status': 'validation_failed',
                'error': {
                    'id': "Cannot find registration with ID {}".format(reg_id),
                },
            })
            return
        except PermissionDenied:
            self.send_json({
                'registration_id': reg_id,
                'registration_data': data,
                'status': 'validation_failed',
                'error': {
                    'id': "You do not have permission to view this "
                    "registration",
                },
            })

    def receive_json(self, content: dict) -> None:
        action = content.get('action', None)
        data = content.get('data', {})

        if action == 'registration':
            self.action_registration(data)
        elif action == 'status':
            self.action_status(data)
        else:
            self.send_json({
                'registration_id': data.get('external_id'),
                'registration_data': data,
                'status': 'validation_failed',
                'error': {
                    'action': 'Action {} is not recognised'.format(action),
                },
            })
