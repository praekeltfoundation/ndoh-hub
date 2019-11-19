import base64
import datetime
import hmac
from hashlib import sha256

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from pytz import UTC
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APITestCase

from eventstore.models import (
    PASSPORT_IDTYPE,
    BabySwitch,
    ChannelSwitch,
    CHWRegistration,
    Event,
    Message,
    OptOut,
    PostbirthRegistration,
    PrebirthRegistration,
    PublicRegistration,
)


class BaseEventTestCase(object):
    def test_authentication_required(self):
        """
        There must be an authenticated user to make the request
        """
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_permission_required(self):
        """
        The authenticated user must have the correct permissions to make the request
        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class OptOutViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("optout-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_optout"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new OptOut object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_optout"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "optout_type": OptOut.STOP_TYPE,
                "reason": OptOut.UNKNOWN_REASON,
                "source": "SMS",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [optout] = OptOut.objects.all()
        self.assertEqual(str(optout.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91")
        self.assertEqual(optout.optout_type, OptOut.STOP_TYPE)
        self.assertEqual(optout.reason, OptOut.UNKNOWN_REASON)
        self.assertEqual(optout.source, "SMS")
        self.assertEqual(optout.created_by, user.username)


class BabySwitchViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("babyswitch-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_babyswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new BabySwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_babyswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {"contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91", "source": "SMS"},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [babyswitch] = BabySwitch.objects.all()
        self.assertEqual(
            str(babyswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(babyswitch.source, "SMS")
        self.assertEqual(babyswitch.created_by, user.username)


class ChannelSwitchViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("channelswitch-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_channelswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new ChannelSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_channelswitch"))
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "source": "SMS",
                "from_channel": "SMS",
                "to_channel": "WhatsApp",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [channelswitch] = ChannelSwitch.objects.all()
        self.assertEqual(
            str(channelswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(channelswitch.source, "SMS")
        self.assertEqual(channelswitch.from_channel, "SMS")
        self.assertEqual(channelswitch.to_channel, "WhatsApp")
        self.assertEqual(channelswitch.created_by, user.username)


class PublicRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("publicregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_publicregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new ChannelSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_publicregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "source": "WhatsApp",
                "language": "zul",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [channelswitch] = PublicRegistration.objects.all()
        self.assertEqual(
            str(channelswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(channelswitch.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(channelswitch.source, "WhatsApp")
        self.assertEqual(channelswitch.language, "zul")
        self.assertEqual(channelswitch.created_by, user.username)


class PrebirthRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("prebirthregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_prebirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new PrebirthRegistration object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_prebirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "zw",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "edd": "2020-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PrebirthRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(registration.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(registration.id_type, PASSPORT_IDTYPE)
        self.assertEqual(registration.id_number, "")
        self.assertEqual(registration.passport_country, "zw")
        self.assertEqual(registration.passport_number, "FN123456")
        self.assertEqual(registration.date_of_birth, None)
        self.assertEqual(registration.language, "zul")
        self.assertEqual(registration.edd, datetime.date(2020, 10, 11))
        self.assertEqual(registration.facility_code, "123456")
        self.assertEqual(registration.source, "WhatsApp")
        self.assertEqual(registration.created_by, user.username)

    def test_prebirth_other_passport_origin(self):
        """
        Should create a new PrebirthRegistration object in the database with
        passport_country = "other"
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_prebirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "other",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "edd": "2020-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PrebirthRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(registration.passport_country, "other")


class PostbirthRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("postbirthregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_postbirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new PostbirthRegistration object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_postbirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "zw",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "baby_dob": "2018-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PostbirthRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(registration.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(registration.id_type, PASSPORT_IDTYPE)
        self.assertEqual(registration.id_number, "")
        self.assertEqual(registration.passport_country, "zw")
        self.assertEqual(registration.passport_number, "FN123456")
        self.assertEqual(registration.date_of_birth, None)
        self.assertEqual(registration.language, "zul")
        self.assertEqual(registration.baby_dob, datetime.date(2018, 10, 11))
        self.assertEqual(registration.facility_code, "123456")
        self.assertEqual(registration.source, "WhatsApp")
        self.assertEqual(registration.created_by, user.username)

    def test_postbirth_other_passport_origin(self):
        """
        Should create a new PostbirthRegistration object in the database with
        passport_country = "other"
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_postbirthregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "other",
                "passport_number": "FN123456",
                "date_of_birth": None,
                "language": "zul",
                "baby_dob": "2018-10-11",
                "facility_code": "123456",
                "source": "WhatsApp",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = PostbirthRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(registration.passport_country, "other")


class MessagesViewSetTests(APITestCase):
    url = reverse("messages-list")

    def generate_hmac_signature(self, data, key):
        data = JSONRenderer().render(data)
        h = hmac.new(key.encode(), data, sha256)
        return base64.b64encode(h.digest()).decode()

    def test_message_identification_required(self):
        """
        There must be identification of user to make the request
        """
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data, {"detail": "Authentication credentials were not provided."}
        )

    def test_message_authentication_required(self):
        """
        The user needs the `add _message` permission
        in order to make the request

        """
        user = get_user_model().objects.create_user("test")
        self.client.force_authenticate(user)
        data = {"random": "data"}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.data,
            {"detail": "You do not have permission to perform this action."},
        )

    def test_message_authentication_errors(self):
        """
        We expect to get auth errors when no user token is added to the querystring,
        but when added the request is made
        """

        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        data = {"random": "data"}

        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        token = Token.objects.create(user=user)
        url = "{}?token={}".format(reverse("messages-list"), str(token.key))
        response = self.client.post(
            url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_incorrect_header_request(self):
        """
        If the header doesn't contain a value that we recognise,
        we should return a 400 Bad Request error,
        explaining that we only accept whatsapp and turn webhook types.
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "statuses": [
                {
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "recipient_id": "16315555555",
                    "status": "read",
                    "timestamp": "1518694700",
                    "random": "data",
                }
            ]
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="other",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {
                "X-Turn-Hook-Subscription": [
                    '"other" is not a valid choice for this header.'
                ]
            },
        )

    def test_missing_hook_subscription_header(self):
        """
        If the hook subscription type header is missing, we should return a descriptive
        error
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data, {"X-Turn-Hook-Subscription": ["This header is required."]}
        )

    def test_missing_field_in_inbound_message_request(self):
        """
        If the data is missing a required field, we should return a
        400 Bad Request error explaining that the field is needed
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {"messages": [{"timestamp": "A"}], "statuses": [{"timestamp": "B"}]}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data,
            {
                "messages": {
                    0: {
                        "id": ["This field is required."],
                        "type": ["This field is required."],
                        "timestamp": ["Invalid POSIX timestamp."],
                    }
                },
                "statuses": {
                    0: {
                        "id": ["This field is required."],
                        "recipient_id": ["This field is required."],
                        "timestamp": ["Invalid POSIX timestamp."],
                        "status": ["This field is required."],
                    }
                },
            },
        )

    def test_outbound_message_validation(self):
        """
        If there are any errors in the body or headers of the request, we should
        return an error with a suitable description
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
            HTTP_X_WHATSAPP_ID="message-id",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"to": ["This field is required."]})

    def test_outbound_message_missing_id(self):
        """
        The header with the message ID is required. If it is not present, a descriptive
        error should be returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {"to": "27820001001"}
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"X-WhatsApp-Id": ["This header is required."]})

    def test_successful_inbound_messages_request(self):
        """
        Should create a new Inbound Message object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "messages": [
                {
                    "id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                    "from": "sender-wa-id",
                    "timestamp": "1518694700",
                    "type": "image",
                    "context": {
                        "from": "sender-wa-id-of-context-message",
                        "group_id": "group-id-of-context-message",
                        "id": "message-id-of-context-message",
                        "mentions": ["wa-id1", "wa-id2"],
                    },
                    "image": {
                        "file": "absolute-filepath-on-coreapp",
                        "id": "media-id",
                        "link": "link-to-image-file",
                        "mime_type": "media-mime-type",
                        "sha256": "checksum",
                        "caption": "image-caption",
                    },
                    "location": {
                        "address": "1 Hacker Way, Menlo Park, CA, 94025",
                        "name": "location-name",
                    },
                    "system": {"body": "system-message-content"},
                    "text": {"body": "text-message-content"},
                    "random": "data",
                }
            ]
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [messages] = Message.objects.all()
        self.assertEqual(str(messages.contact_id), "sender-wa-id")
        self.assertEqual(
            messages.timestamp, datetime.datetime(2018, 2, 15, 11, 38, 20, tzinfo=UTC)
        ),
        self.assertEqual(messages.id, "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"),
        self.assertEqual(messages.type, "image"),
        self.assertEqual(messages.message_direction, Message.INBOUND),
        self.assertEqual(
            messages.data,
            {
                "context": {
                    "from": "sender-wa-id-of-context-message",
                    "group_id": "group-id-of-context-message",
                    "id": "message-id-of-context-message",
                    "mentions": ["wa-id1", "wa-id2"],
                },
                "image": {
                    "file": "absolute-filepath-on-coreapp",
                    "id": "media-id",
                    "link": "link-to-image-file",
                    "mime_type": "media-mime-type",
                    "sha256": "checksum",
                    "caption": "image-caption",
                },
                "location": {
                    "address": "1 Hacker Way, Menlo Park, CA, 94025",
                    "name": "location-name",
                },
                "system": {"body": "system-message-content"},
                "text": {"body": "text-message-content"},
                "random": "data",
            },
        ),
        self.assertEqual(messages.created_by, user.username)

    def test_successful_outbound_messages_request(self):
        """
        Should create a new Outbound Message object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "preview_url": True,
            "render_mentions": True,
            "recipient_type": "individual",
            "to": "whatsapp-id",
            "type": "text",
            "text": {"body": "your-text-message-content"},
            "random": "data",
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="turn",
            HTTP_X_WHATSAPP_ID="message-id",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [messages] = Message.objects.all()
        self.assertEqual(str(messages.contact_id), "whatsapp-id")
        self.assertEqual(messages.id, "message-id"),
        self.assertEqual(messages.type, "text"),
        self.assertEqual(messages.message_direction, Message.OUTBOUND),
        self.assertEqual(
            messages.data,
            {
                "text": {"body": "your-text-message-content"},
                "render_mentions": True,
                "preview_url": True,
                "random": "data",
                "recipient_type": "individual",
            },
        ),
        self.assertEqual(messages.created_by, user.username)

    def test_successful_events_request(self):
        """
        Should create a new Event object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {
            "statuses": [
                {
                    "id": "ABGGFlA5FpafAgo6tHcNmNjXmuSf",
                    "recipient_id": "16315555555",
                    "status": "read",
                    "timestamp": "1518694700",
                    "random": "data",
                }
            ]
        }
        response = self.client.post(
            self.url,
            data,
            format="json",
            HTTP_X_TURN_HOOK_SIGNATURE=self.generate_hmac_signature(data, "REPLACEME"),
            HTTP_X_TURN_HOOK_SUBSCRIPTION="whatsapp",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [event] = Event.objects.all()
        self.assertEqual(str(event.message_id), "ABGGFlA5FpafAgo6tHcNmNjXmuSf")
        self.assertEqual(str(event.recipient_id), "16315555555")
        self.assertEqual(event.status, "read")
        self.assertEqual(
            event.timestamp, datetime.datetime(2018, 2, 15, 11, 38, 20, tzinfo=UTC)
        )
        self.assertEqual(event.created_by, user.username)
        self.assertEqual(event.data, {"random": "data"})

    def test_signature_required(self):
        """
        Should see if the signature hook is given,
        otherwise, return a 401
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {}
        response = self.client.post(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(
            response.data, {"detail": "X-Turn-Hook-Signature header required"}
        )

    def test_signature_valid(self):
        """
        If the HMAC signature is invalid, we should return a descriptive error
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(Permission.objects.get(codename="add_message"))
        self.client.force_authenticate(user)
        data = {}
        response = self.client.post(
            self.url, data, format="json", HTTP_X_TURN_HOOK_SIGNATURE="foo"
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data, {"detail": "Invalid hook signature"})


class CHWRegistrationViewSetTests(APITestCase, BaseEventTestCase):
    url = reverse("chwregistration-list")

    def test_data_validation(self):
        """
        The supplied data must be validated, and any errors returned
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_chwregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_successful_request(self):
        """
        Should create a new ChannelSwitch object in the database
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_chwregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "source": "WhatsApp",
                "id_type": "dob",
                "id_number": "",
                "passport_country": "",
                "passport_number": "",
                "date_of_birth": "1990-02-03",
                "language": "nso",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [channelswitch] = CHWRegistration.objects.all()
        self.assertEqual(
            str(channelswitch.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(
            str(channelswitch.device_contact_id), "d80d51cb-8a95-4588-ac74-250d739edef8"
        )
        self.assertEqual(channelswitch.source, "WhatsApp")
        self.assertEqual(channelswitch.id_type, "dob")
        self.assertEqual(channelswitch.date_of_birth, datetime.date(1990, 2, 3))
        self.assertEqual(channelswitch.language, "nso")
        self.assertEqual(channelswitch.created_by, user.username)

    def test_chw_other_passport_origin(self):
        """
        Should create a new CHWRegistration object in the database with
        passport_country = "other"
        """
        user = get_user_model().objects.create_user("test")
        user.user_permissions.add(
            Permission.objects.get(codename="add_chwregistration")
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            self.url,
            {
                "contact_id": "9e12d04c-af25-40b6-aa4f-57c72e8e3f91",
                "device_contact_id": "d80d51cb-8a95-4588-ac74-250d739edef8",
                "source": "WhatsApp",
                "id_type": "passport",
                "id_number": "",
                "passport_country": "other",
                "passport_number": "",
                "date_of_birth": "1990-02-03",
                "language": "nso",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        [registration] = CHWRegistration.objects.all()
        self.assertEqual(
            str(registration.contact_id), "9e12d04c-af25-40b6-aa4f-57c72e8e3f91"
        )
        self.assertEqual(registration.passport_country, "other")
