import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User

from registrations.consumers import JembiAppRegistrationConsumer


@database_sync_to_async
def create_user() -> User:
    return User.objects.create_user('test')


@database_sync_to_async
def cleanup_user(user: User) -> None:
    user.delete()


async def create_communicator(user: User) -> WebsocketCommunicator:
    """
    Creates and returns the communicator
    """
    communicator = WebsocketCommunicator(
        JembiAppRegistrationConsumer, '/api/v1/jembiregistration/')

    # Add user to scope, like the middleware would
    communicator.scope['user'] = user

    connected, _ = await communicator.connect()
    assert connected
    return communicator


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_echo_consumer_unauthorized() -> None:
    """
    If no user is set by the middleware, then the connection should be denied
    """
    communicator = WebsocketCommunicator(
        JembiAppRegistrationConsumer, '/api/v1/jembiregistration/')

    # Add user to scope, like the middleware would
    communicator.scope['user'] = None

    connected, code = await communicator.connect()
    assert connected is False


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_unrecognised_action() -> None:
    """
    If an invalid action is given, then a validation error should be returned
    """
    user = await create_user()
    communicator = await create_communicator(user)

    await communicator.send_json_to({
        'action': 'invalid',
        'data': {
            'external_id': 'test-external',
        },
    })
    response = await communicator.receive_json_from()
    assert response == {
        'registration_id': 'test-external',
        'registration_data': {
            'external_id': 'test-external',
        },
        'status': 'validation_failed',
        'error': {
            'action': 'Action invalid is not recognised',
        },
    }

    await communicator.disconnect()
    await cleanup_user(user)
