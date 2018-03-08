import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User

from registrations.consumers import EchoConsumer


@database_sync_to_async
def create_user():
    return User.objects.create_user('test')


@database_sync_to_async
def cleanup_user(user):
    return user.delete()


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_echo_consumer_echos():
    """
    The echo consumer should echo back any JSON sent to it
    """
    communicator = WebsocketCommunicator(EchoConsumer, '/echo/')

    # Add user to scope, like the middleware would
    user = await create_user()
    communicator.scope['user'] = user

    connected, _ = await communicator.connect()
    assert connected
    await communicator.send_json_to({'foo': 'bar'})
    response = await communicator.receive_json_from()
    assert response == {'foo': 'bar'}
    await communicator.disconnect()
    await cleanup_user(user)


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_echo_consumer_unauthorized():
    """
    If no user is set by the middleware, then the connection should be denied
    """
    communicator = WebsocketCommunicator(EchoConsumer, '/echo/')

    # Add user to scope, like the middleware would
    communicator.scope['user'] = None

    connected, code = await communicator.connect()
    assert connected is False
