from channels.generic.websocket import JsonWebsocketConsumer


class JembiAppRegistrationConsumer(JsonWebsocketConsumer):
    def connect(self) -> None:
        self.user = self.scope['user']
        if self.user and self.user.is_authenticated:
            self.accept()
        else:
            self.close()

    def receive_json(self, content: dict) -> None:
        action = content.get('action', None)
        data = content.get('data', {})

        if action == 'registration':
            # TODO: Add registration logic
            pass
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
