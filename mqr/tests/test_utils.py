import responses
from datetime import datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

from mqr.utils import get_tag, get_message, get_message_details, get_next_send_date


class TestGetTag(TestCase):
    def test_get_tag(self):
        """
        Returns the correct tag
        """
        self.assertEqual(
            get_tag("RCM", "pre", datetime.today().date()), "RCM_week_pre0"
        )

        few_weeks_ago = datetime.today().date() - timedelta(days=23)
        self.assertEqual(get_tag("BCM", "post", few_weeks_ago), "BCM_week_post3")

    def test_get_tag_with_sequence(self):
        """
        Returns the correct tag with a sequence
        """
        self.assertEqual(
            get_tag("RCM", "pre", datetime.today().date(), "a"), "RCM_week_pre0_a"
        )

        few_weeks_ago = datetime.today().date() - timedelta(days=23)
        self.assertEqual(get_tag("BCM", "post", few_weeks_ago), "BCM_week_post3")


class TestGetMessage(TestCase):
    @responses.activate
    def test_get_message_non_template(self):
        """
        Returns the message body
        """
        responses.add(
            responses.GET,
            "http://contentrepo/api/v2/pages/1111/?whatsapp=True",
            json={"body": {"text": {"value": {"message": "Test Message"}}}},
            status=200,
        )
        is_template, message = get_message(1111)
        self.assertFalse(is_template)
        self.assertEqual(message, "Test Message")

    @responses.activate
    def test_get_message_template(self):
        """
        Returns the message body
        """
        responses.add(
            responses.GET,
            "http://contentrepo/api/v2/pages/1111/?whatsapp=True",
            json={
                "body": {"text": {"value": {"message": "Test Message"}}},
                "is_whatsapp_template": True,
                "title": "BCM_POST_week_3_123123",
            },
            status=200,
        )
        is_template, message = get_message(1111)
        self.assertTrue(is_template)
        self.assertEqual(message, "BCM_POST_week_3_123123")


class TestGetMessageDetails(TestCase):
    @responses.activate
    def test_get_message_details_not_found(self):
        tag = "BCM_POST_week_3"
        responses.add(
            responses.GET,
            f"http://contentrepo/api/v2/pages?tag={tag}",
            json={"results": []},
            status=200,
        )

        details = get_message_details(tag)

        self.assertEqual(details, {"error": "no message found"})

    @responses.activate
    def test_get_message_details_too_many(self):
        tag = "BCM_POST_week_3"
        responses.add(
            responses.GET,
            f"http://contentrepo/api/v2/pages?tag={tag}",
            json={"results": [1, 2]},
            status=200,
        )

        details = get_message_details(tag)

        self.assertEqual(details, {"error": "multiple message found"})

    @responses.activate
    @patch("mqr.utils.get_message")
    def test_get_message_details(self, mock_get_message):
        mock_get_message.return_value = (False, "Test Message")

        tag = "BCM_POST_week_3"
        responses.add(
            responses.GET,
            f"http://contentrepo/api/v2/pages?tag={tag}",
            json={"results": [{"id": 1111}]},
            status=200,
        )

        details = get_message_details(tag)

        self.assertEqual(details, {"is_template": False, "message": "Test Message"})


class TestGetNextSendDate(TestCase):
    def test_get_next_send_date(self):
        today = datetime.today().date()
        next_date = get_next_send_date()

        self.assertEqual(next_date, today + timedelta(weeks=1))
