from channels.generic.websocket import JsonWebsocketConsumer


class EchoConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.user = self.scope['user']
        if self.user and self.user.is_authenticated:
            self.accept()
        else:
            self.close()

    def receive_json(self, content):
        self.send_json(content)
