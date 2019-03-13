import csv
import json
import unittest
from io import StringIO
from unittest.mock import patch

import responses
from requests.exceptions import HTTPError

from scripts.migrate_to_whatsapp_templates import template_submission


class TemplateSubmissionTests(unittest.TestCase):
    def test_parse_arguments_default(self):
        """ Defaults to execute being false """
        arguments = template_submission.parse_arguments([])
        self.assertEqual(arguments.execute, False)
        self.assertEqual(arguments.token, None)

    def test_parse_arguments_non_default(self):
        """ Specifying execute makes it true, value of token is stored """
        arguments = template_submission.parse_arguments(
            ["--execute", "--token", "test-token"]
        )
        self.assertEqual(arguments.execute, True)
        self.assertEqual(arguments.token, "test-token")

    def test_whatsapp_api_format(self):
        """ Returns dictionary in correct format for WhatsApp API """
        result = template_submission.whatsapp_api_format(
            {
                "name": "test_name",
                "language": "zul_ZA",
                "content": "Test template {{1}}",
            }
        )
        self.assertEqual(
            result,
            {
                "category": "ALERT_UPDATE",
                "content": "Test template {{1}}",
                "name": "test_name",
                "language": "uz",
            },
        )

    @responses.activate
    def test_submit_to_whatsapp(self):
        """ Submits in the correct format with the correct headers """
        responses.add(
            responses.POST,
            "https://whatsapp.praekelt.org/v1/message_templates",
            json={},
            status=200,
        )
        data = {
            "category": "ALERT_UPDATE",
            "content": "Test template {{1}}",
            "name": "test_name",
            "language": "uz",
        }
        template_submission.submit_to_whatsapp("test-token", data)

        [call] = responses.calls
        self.assertEqual(json.loads(call.request.body), data)
        self.assertEqual(call.request.headers["Authorization"], "Bearer test-token")
        self.assertEqual(call.request.headers["Accept"], "application/vnd.v1+json")

    @responses.activate
    def test_submit_to_whatsapp_failure(self):
        """ Should raise an exception on invalid status code response """
        responses.add(
            responses.POST,
            "https://whatsapp.praekelt.org/v1/message_templates",
            json={},
            status=500,
        )
        data = {
            "category": "ALERT_UPDATE",
            "content": "Test template {{1}}",
            "name": "test_name",
            "language": "uz",
        }
        with self.assertRaises(HTTPError):
            template_submission.submit_to_whatsapp("test-token", data)

    @patch(
        "scripts.migrate_to_whatsapp_templates.template_submission.submit_to_whatsapp"
    )
    def test_run(self, submit_mock):
        """ Submits to WhatsApp if execute is selected """
        input = StringIO()

        writer = csv.writer(input)
        writer.writerow(["name", "language", "content"])
        writer.writerow(["test1", "zul_ZA", "testcontent1"])
        writer.writerow(["test2", "afr_ZA", "testcontent2"])

        input = StringIO(input.getvalue())
        output = StringIO()

        template_submission.run(input, output, ["--execute", "--token", "test-token"])

        submit_mock.assert_any_call(
            "test-token",
            {
                "category": "ALERT_UPDATE",
                "content": "testcontent1",
                "name": "test1",
                "language": "uz",
            },
        )

        submit_mock.assert_any_call(
            "test-token",
            {
                "category": "ALERT_UPDATE",
                "content": "testcontent2",
                "name": "test2",
                "language": "af",
            },
        )

    @responses.activate
    def test_dry_run(self):
        """ If --execute isn't supplied, no HTTP calls should be made """
        input = StringIO()

        writer = csv.writer(input)
        writer.writerow(["name", "language", "content"])
        writer.writerow(["test1", "zul_ZA", "testcontent1"])
        writer.writerow(["test2", "afr_ZA", "testcontent2"])

        input = StringIO(input.getvalue())
        output = StringIO()

        template_submission.run(input, output, ["--token", "test-token"])

        self.assertEqual(len(responses.calls), 0)

        self.assertEqual(
            [json.loads(o) for o in output.getvalue().strip().split("\n")],
            [
                {
                    "category": "ALERT_UPDATE",
                    "content": "testcontent1",
                    "name": "test1",
                    "language": "uz",
                },
                {
                    "category": "ALERT_UPDATE",
                    "content": "testcontent2",
                    "name": "test2",
                    "language": "af",
                },
            ],
        )
