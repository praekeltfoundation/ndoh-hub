from datetime import date, datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

import responses

from mqr import utils


def override_get_today():
    return datetime.strptime("20220301", "%Y%m%d").date()


class TestGetTag(TestCase):
    def test_get_tag(self):
        """
        Returns the correct tag
        """
        self.assertEqual(
            utils.get_tag("RCM", "pre", datetime.today().date()), "RCM_week_pre0"
        )

        few_weeks_ago = datetime.today().date() - timedelta(days=23)
        self.assertEqual(utils.get_tag("BCM", "post", few_weeks_ago), "BCM_week_post3")

    def test_get_tag_with_sequence(self):
        """
        Returns the correct tag with a sequence
        """
        self.assertEqual(
            utils.get_tag("RCM", "pre", datetime.today().date(), "a"), "RCM_week_pre0_a"
        )

        few_weeks_ago = datetime.today().date() - timedelta(days=23)
        self.assertEqual(utils.get_tag("BCM", "post", few_weeks_ago), "BCM_week_post3")


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
        is_template, has_parameters, message = utils.get_message(1111)
        self.assertFalse(is_template)
        self.assertFalse(has_parameters)
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
        is_template, has_parameters, message = utils.get_message(1111)
        self.assertTrue(is_template)
        self.assertFalse(has_parameters)
        self.assertEqual(message, "BCM_POST_week_3_123123")

    @responses.activate
    def test_get_message_template_with_parameters(self):
        """
        Returns the message body
        """
        responses.add(
            responses.GET,
            "http://contentrepo/api/v2/pages/1111/?whatsapp=True",
            json={
                "body": {"text": {"value": {"message": "Test Message {{1}}"}}},
                "is_whatsapp_template": True,
                "title": "BCM_POST_week_3_123123",
            },
            status=200,
        )
        is_template, has_parameters, message = utils.get_message(1111)
        self.assertTrue(is_template)
        self.assertTrue(has_parameters)
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

        details = utils.get_message_details(tag)

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

        details = utils.get_message_details(tag)

        self.assertEqual(details, {"error": "multiple message found"})

    @responses.activate
    @patch("mqr.utils.get_message")
    def test_get_message_details(self, mock_get_message):
        mock_get_message.return_value = (False, False, "Test Message {{1}}")

        tag = "BCM_POST_week_3"
        responses.add(
            responses.GET,
            f"http://contentrepo/api/v2/pages?tag={tag}",
            json={"results": [{"id": 1111}]},
            status=200,
        )

        details = utils.get_message_details(tag, "Mom")

        self.assertEqual(
            details,
            {
                "is_template": False,
                "has_parameters": False,
                "message": "Test Message Mom",
            },
        )


class TestGetNextMessage(TestCase):
    def setUp(self):
        utils.get_today = override_get_today

    @patch("mqr.utils.get_message_details")
    def test_get_next_message(self, mock_get_message_details):

        mock_get_message_details.return_value = {
            "is_template": False,
            "has_parameters": False,
            "message": "Test Message Mom",
        }

        edd = datetime.strptime("20220701", "%Y%m%d").date()
        response = utils.get_next_message(edd, "pre", "RCM", None, "Mom")

        print(response)

        self.assertEqual(
            response,
            {
                "is_template": False,
                "has_parameters": False,
                "message": "Test Message Mom",
                "next_send_date": utils.get_next_send_date(),
                "tag": "RCM_week_pre17",
            },
        )


class TestGetNextSendDate(TestCase):
    def setUp(self):
        utils.get_today = override_get_today

    def test_get_next_send_date(self):
        next_date = utils.get_next_send_date()
        self.assertEqual(next_date, date(2022, 3, 8))
