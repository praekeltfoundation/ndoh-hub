from channels.generic.websocket import JsonWebsocketConsumer
from rest_framework.exceptions import ValidationError

from registrations.views import JembiAppRegistration


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

    def receive_json(self, content: dict) -> None:
        action = content.get('action', None)
        data = content.get('data', {})

        if action == 'registration':
            self.action_registration(data)
        elif action == 'status':
            # TODO: Add status logic
            pass
        else:
            self.send_json({
                'registration_id': data.get('external_id'),
                'registration_data': data,
                'status': 'validation_failed',
                'error': {
                    'action': 'Action {} is not recognised'.format(action),
                },
            })
