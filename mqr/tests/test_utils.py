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
            utils.get_tag("RCM", "pre", datetime.today().date()), "rcm_week_pre0"
        )

        few_weeks_ago = datetime.today().date() - timedelta(days=23)
        self.assertEqual(utils.get_tag("BCM", "post", few_weeks_ago), "bcm_week_post3")

    def test_get_tag_with_sequence(self):
        """
        Returns the correct tag with a sequence
        """
        self.assertEqual(
            utils.get_tag("RCM", "pre", datetime.today().date(), "a"), "rcm_week_pre0_a"
        )

        few_weeks_ago = datetime.today().date() - timedelta(days=23)
        self.assertEqual(utils.get_tag("BCM", "post", few_weeks_ago), "bcm_week_post3")


class TestGetMessage(TestCase):
    @responses.activate
    def test_get_message_non_template(self):
        """
        Returns the message body
        """
        responses.add(
            responses.GET,
            "http://contentrepo/api/v2/pages/1111/?whatsapp=True&tracking=yes",
            json={"body": {"text": {"value": {"message": "Test Message"}}}},
            status=200,
        )
        is_template, has_parameters, message = utils.get_message(
            1111, {"tracking": "yes"}
        )
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
            "http://contentrepo/api/v2/pages/1111/?whatsapp=True&tracking=yes",
            json={
                "body": {"text": {"value": {"message": "Test Message"}}},
                "is_whatsapp_template": True,
                "title": "bcm_week_post3_123123",
            },
            status=200,
        )
        is_template, has_parameters, message = utils.get_message(
            1111, {"tracking": "yes"}
        )
        self.assertTrue(is_template)
        self.assertFalse(has_parameters)
        self.assertEqual(message, "bcm_week_post3_123123")

    @responses.activate
    def test_get_message_template_with_parameters(self):
        """
        Returns the message body
        """
        responses.add(
            responses.GET,
            "http://contentrepo/api/v2/pages/1111/?whatsapp=True&tracking=yes",
            json={
                "body": {"text": {"value": {"message": "Test Message {{1}}"}}},
                "is_whatsapp_template": True,
                "title": "bcm_week_post3_123123",
            },
            status=200,
        )
        is_template, has_parameters, message = utils.get_message(
            1111, {"tracking": "yes"}
        )
        self.assertTrue(is_template)
        self.assertTrue(has_parameters)
        self.assertEqual(message, "bcm_week_post3_123123")


class TestGetMessageDetails(TestCase):
    @responses.activate
    def test_get_message_details_not_found(self):
        tag = "bcm_week_post3"
        responses.add(
            responses.GET,
            f"http://contentrepo/api/v2/pages?tag={tag}",
            json={"results": []},
            status=200,
        )

        details = utils.get_message_details(tag, {})

        self.assertEqual(details, {"error": "no message found"})

    @responses.activate
    def test_get_message_details_not_found_arm(self):
        tag = "arm_week_post3"
        responses.add(
            responses.GET,
            f"http://contentrepo/api/v2/pages?tag={tag}",
            json={"results": []},
            status=200,
        )

        details = utils.get_message_details(tag, {})

        self.assertEqual(details, {"warning": "no message found"})

    @responses.activate
    def test_get_message_details_too_many(self):
        tag = "bcm_week_post3"
        responses.add(
            responses.GET,
            f"http://contentrepo/api/v2/pages?tag={tag}",
            json={"results": [1, 2]},
            status=200,
        )

        details = utils.get_message_details(tag, {})

        self.assertEqual(details, {"error": "multiple message found"})

    @responses.activate
    @patch("mqr.utils.get_message")
    def test_get_message_details(self, mock_get_message):
        mock_get_message.return_value = (False, False, "Test Message {{1}}")

        tag = "bcm_week_post3"
        responses.add(
            responses.GET,
            f"http://contentrepo/api/v2/pages?tag={tag}",
            json={"results": [{"id": 1111}]},
            status=200,
        )

        details = utils.get_message_details(tag, {}, "Mom")

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
        response = utils.get_next_message(edd, "pre", "RCM", None, "Mom", {})

        self.assertEqual(
            response,
            {
                "is_template": False,
                "has_parameters": False,
                "message": "Test Message Mom",
                "next_send_date": utils.get_next_send_date(),
                "tag": "rcm_week_pre17",
            },
        )

    @responses.activate
    @patch("mqr.utils.get_message_details")
    def test_get_next_message_with_sequence(self, mock_get_message_details):

        mock_get_message_details.return_value = {
            "is_template": False,
            "has_parameters": False,
            "message": "Test Message Mom",
        }

        responses.add(
            responses.GET,
            "http://contentrepo/api/v2/pages?tag=rcm_week_pre17_b",
            json={"results": [{"id": 1111}]},
            status=200,
        )

        edd = datetime.strptime("20220701", "%Y%m%d").date()
        response = utils.get_next_message(edd, "pre", "RCM", "a", "Mom", {})

        message_prompt = "To get another helpful message tomorrow, reply *YES*."

        self.assertEqual(
            response,
            {
                "has_next_message": True,
                "is_template": False,
                "has_parameters": False,
                "message": f"Test Message Mom\n\n{message_prompt}",
            },
        )

    @responses.activate
    @patch("mqr.utils.get_message_details")
    def test_get_next_message_with_sequence_last(self, mock_get_message_details):

        mock_get_message_details.return_value = {
            "is_template": False,
            "has_parameters": False,
            "message": "Test Message Mom",
        }

        responses.add(
            responses.GET,
            "http://contentrepo/api/v2/pages?tag=rcm_week_pre17_b",
            json={"results": []},
            status=200,
        )

        edd = datetime.strptime("20220701", "%Y%m%d").date()
        response = utils.get_next_message(edd, "pre", "RCM", "a", "Mom", {})

        message_prompt = "-----\nReply:\n*MENU* for the main menu 📌"

        self.assertEqual(
            response,
            {
                "has_next_message": False,
                "is_template": False,
                "has_parameters": False,
                "message": f"Test Message Mom\n\n{message_prompt}",
            },
        )

    @responses.activate
    @patch("mqr.utils.get_message_details")
    def test_get_next_message_with_sequence_and_existing_prompt(
        self, mock_get_message_details
    ):

        mock_get_message_details.return_value = {
            "is_template": False,
            "has_parameters": False,
            "message": "Test Message Mom\n\nTo get more information about coping "
            "after the birth, reply *YES*.",
        }

        responses.add(
            responses.GET,
            "http://contentrepo/api/v2/pages?tag=rcm_week_pre17_b",
            json={"results": [{"id": 1111}]},
            status=200,
        )

        edd = datetime.strptime("20220701", "%Y%m%d").date()
        response = utils.get_next_message(edd, "pre", "RCM", "a", "Mom", {})

        self.assertEqual(
            response,
            {
                "has_next_message": True,
                "is_template": False,
                "has_parameters": False,
                "message": "Test Message Mom\n\nTo get more information about coping "
                "after the birth, reply *YES*.",
            },
        )


class TestGetFaqMessage(TestCase):
    @patch("mqr.utils.get_faq_menu")
    @patch("mqr.utils.get_message_details")
    def test_get_faq_message(self, mock_get_message_details, mock_get_faq_menu):
        mock_get_message_details.return_value = {
            "is_template": False,
            "has_parameters": False,
            "message": "Test Message Mom",
        }
        mock_get_faq_menu.return_value = ("*1* question1?\n*2* question 2?", "1,3")

        response = utils.get_faq_message("rcm_week_pre21", 2, [], {})

        self.assertEqual(
            response,
            {
                "is_template": False,
                "has_parameters": False,
                "message": "Test Message Mom",
                "faq_menu": "*1* question1?\n*2* question 2?",
                "faq_numbers": "1,3",
                "viewed": ["rcm_week_pre21_faq2"],
            },
        )

        mock_get_faq_menu.assert_called_with(
            "rcm_week_pre21", ["rcm_week_pre21_faq2"], False
        )

    @patch("mqr.utils.get_faq_menu")
    @patch("mqr.utils.get_message_details")
    def test_get_faq_message_rcm_bcm(self, mock_get_message_details, mock_get_faq_menu):
        mock_get_message_details.return_value = {
            "is_template": False,
            "has_parameters": False,
            "message": "Test Message Mom",
        }
        mock_get_faq_menu.return_value = ("*1* question1?\n*2* question 2?", "1,3")

        response = utils.get_faq_message("rcm_bcm_week_pre21", 2, [], {})

        self.assertEqual(
            response,
            {
                "is_template": False,
                "has_parameters": False,
                "message": "Test Message Mom",
                "faq_menu": "*1* question1?\n*2* question 2?",
                "faq_numbers": "1,3",
                "viewed": ["rcm_week_pre21_faq2"],
            },
        )

        mock_get_faq_menu.assert_called_with(
            "rcm_week_pre21", ["rcm_week_pre21_faq2"], True
        )


class TestGetFaqMenu(TestCase):
    @responses.activate
    def test_get_faq_menu(self):
        tag = "rcm_week_pre21"
        responses.add(
            responses.GET,
            f"http://contentrepo/faqmenu?viewed=&tag={tag}",
            json=[
                {"order": 1, "title": "Question 1?"},
                {"order": 3, "title": "Question 3?"},
            ],
            status=200,
        )

        menu, faq_numbers = utils.get_faq_menu(tag, [], False)

        self.assertEqual(menu, "*1* - Question 1?\n*2* - Question 3?")
        self.assertEqual(faq_numbers, "1,3")

    @responses.activate
    def test_get_faq_menu_with_viewed(self):
        tag = "rcm_week_pre21"
        responses.add(
            responses.GET,
            f"http://contentrepo/faqmenu?viewed={tag}_faq1&tag={tag}",
            json=[
                {"order": 1, "title": "Question 1?"},
                {"order": 3, "title": "Question 3?"},
            ],
            status=200,
        )

        menu, faq_numbers = utils.get_faq_menu(tag, [f"{tag}_faq1"], False)

        self.assertEqual(menu, "*1* - Question 1?\n*2* - Question 3?")
        self.assertEqual(faq_numbers, "1,3")

    @responses.activate
    def test_get_faq_menu_bcm(self):
        tag = "rcm_week_pre21"
        responses.add(
            responses.GET,
            f"http://contentrepo/faqmenu?viewed=&tag={tag}",
            json=[
                {"order": 1, "title": "Question 1?"},
                {"order": 3, "title": "Question 3?"},
            ],
            status=200,
        )

        menu, faq_numbers = utils.get_faq_menu(tag, [], True)

        test_menu = [
            "*1* - Question 1?",
            "*2* - Question 3?",
            "*3* - *FIND* more topics 🔎",
        ]

        self.assertEqual(menu, "\n".join(test_menu))
        self.assertEqual(faq_numbers, "1,3")

    @responses.activate
    def test_get_faq_menu_with_menu_offset(self):
        tag = "rcm_week_pre21"
        responses.add(
            responses.GET,
            f"http://contentrepo/faqmenu?viewed=&tag={tag}",
            json=[
                {"order": 1, "title": "Question 1?"},
                {"order": 3, "title": "Question 3?"},
            ],
            status=200,
        )

        menu, faq_numbers = utils.get_faq_menu(tag, [], False, 3)

        self.assertEqual(menu, "*4* - Question 1?\n*5* - Question 3?")
        self.assertEqual(faq_numbers, "1,3")


class TestGetNextSendDate(TestCase):
    def setUp(self):
        utils.get_today = override_get_today

    def test_get_next_send_date(self):
        next_date = utils.get_next_send_date()
        self.assertEqual(next_date, date(2022, 3, 8))
