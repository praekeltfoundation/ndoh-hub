from unittest import TestCase

from eventstore.models import Message


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
