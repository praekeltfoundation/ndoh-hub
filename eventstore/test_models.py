from unittest import TestCase

from eventstore.models import Event, Message


class MessageTests(TestCase):
    def test_is_operator_message(self):
        """
        Whether this message is from an operator or not
        """
        msg = Message(
            message_direction=Message.OUTBOUND,
            type="text",
            data={
                "_vnd": {
                    "v1": {
                        "author": {"type": "OPERATOR"},
                        "chat": {"owner": "27820001001"},
                    }
                }
            },
        )
        self.assertEqual(msg.is_operator_message, True)
        msg.data = {}
        self.assertEqual(msg.is_operator_message, False)


class EventTests(TestCase):
    def test_is_hsm_error(self):
        """
        Is this event a hsm error
        """
        event = Event(
            fallback_channel=False,
            data={"errors": [{"title": "structure unavailable"}]},
        )
        self.assertTrue(event.is_hsm_error)

        event.data = {"errors": [{"title": "envelope mismatch"}]}
        self.assertTrue(event.is_hsm_error)

        event.data = {"errors": [{"title": "something else"}]}
        self.assertFalse(event.is_hsm_error)

        event.fallback_channel = True
        event.data = {"errors": [{"title": "envelope mismatch"}]}
        self.assertFalse(event.is_hsm_error)

    def test_is_message_expired_error(self):
        """
        Is this event a message expired error
        """
        event = Event(fallback_channel=False, data={"errors": [{"code": 410}]})
        self.assertTrue(event.is_message_expired_error)

        event = Event(fallback_channel=False, data={"errors": [{"code": 111}]})
        self.assertFalse(event.is_message_expired_error)

        event = Event(fallback_channel=True, data={"errors": [{"code": 410}]})
        self.assertFalse(event.is_message_expired_error)
