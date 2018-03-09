import datetime
import pytest
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from unittest import mock

from registrations import views
from registrations.consumers import JembiAppRegistrationConsumer
from registrations.models import Source
from ndoh_hub import utils


@database_sync_to_async
def create_user() -> User:
    user = User.objects.create_user('test')
    Source.objects.create(user=user)
    return user


@database_sync_to_async
def cleanup_user(user: User) -> None:
    user.sources.all().delete()
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


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_registration_validation_error() -> None:
    """
    For the registration action, if there is a validation error, it should be
    returned.
    """
    user = await create_user()
    communicator = await create_communicator(user)

    await communicator.send_json_to({
        'action': 'registration',
        'data': {
            'external_id': 'test-external',
        },
    })
    response = await communicator.receive_json_from()
    assert response['registration_id'] == 'test-external'
    assert response['registration_data'] == {
        'external_id': 'test-external',
    }
    assert response['status'] == 'validation_failed'
    assert response['error']['mom_edd'] == ['This field is required.']

    await communicator.disconnect()
    await cleanup_user(user)


@pytest.mark.asyncio
@pytest.mark.django_db
async def test_registration_valid() -> None:
    """
    For the registration action, if it is valid, then it should be sent to the
    celery task.
    """
    old_today = utils.get_today
    today = utils.get_today = mock.MagicMock()
    today.return_value = datetime.datetime(2016, 1, 1).date()

    old_task = views.validate_subscribe_jembi_app_registration
    task = views.validate_subscribe_jembi_app_registration = mock.MagicMock()

    user = await create_user()
    communicator = await create_communicator(user)

    await communicator.send_json_to({
        'action': 'registration',
        'data': {
            'external_id': 'test-external-id',
            'mom_edd': '2016-06-06',
            'mom_msisdn': '+27820000000',
            'mom_consent': True,
            'created': '2016-01-01 00:00:00',
            'hcw_msisdn': '+27821111111',
            'clinic_code': '123456',
            'mom_lang': 'eng_ZA',
            'mha': 1,
            'mom_dob': '1988-01-01',
            'mom_id_type': 'none',
        },
    })

    await communicator.disconnect()

    task.delay.assert_called_once()

    await cleanup_user(user)
    utils.get_today = old_today
    views.validate_subscribe_jembi_app_registration = old_task
