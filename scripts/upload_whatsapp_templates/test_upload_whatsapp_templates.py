import json
from io import StringIO
from unittest import TestCase
from unittest.mock import MagicMock

from scripts.upload_whatsapp_templates.upload_whatsapp_templates import (
    Template,
    parse_templates,
    submit_template,
)


class UploadWhatsAppTemplatesTests(TestCase):
    def test_template_category(self):
        """
        Templates should only accept certain values for the category
        """
        with self.assertRaises(ValueError):
            Template(category="FOO", body="body", name="name", language="en")

    def test_template_body(self):
        """
        Template body must be a string, and must be <= 1024 characters long
        """
        with self.assertRaises(TypeError):
            Template(category="ACCOUNT_UPDATE", body=7, name="name", language="en")
        with self.assertRaises(ValueError):
            Template(
                category="ACCOUNT_UPDATE", body="a" * 1025, name="name", language="en"
            )

    def test_template_language(self):
        """
        Template language must be one of the valid choices
        """
        with self.assertRaises(ValueError):
            Template(category="ACCOUNT_UPDATE", body="body", name="name", language="f")

    def test_parse_templates(self):
        """
        Should return a valid list of templates from the CSV file
        """

        args = MagicMock()
        args.category = "category"
        args.body = "body"
        args.name = "name"
        args.language = "language"
        args.csv_file = StringIO(
            "category,body,name,language\n"
            "ACCOUNT_UPDATE,body1,name1,en\n"
            "PAYMENT_UPDATE,body2,name2,af\n"
        )

        [template1, template2] = parse_templates(args)
        self.assertEqual(
            template1,
            Template(
                category="ACCOUNT_UPDATE", body="body1", name="name1", language="en"
            ),
        )
        self.assertEqual(
            template2,
            Template(
                category="PAYMENT_UPDATE", body="body2", name="name2", language="af"
            ),
        )

    def test_submit_template(self):
        """
        Should submit the template to the API, with the components double json encoded
        """
        args = MagicMock()
        args.base_url = "https://example.org"
        args.number = "27820001001"

        session = MagicMock()

        submit_template(
            args,
            session,
            Template(
                category="ACCOUNT_UPDATE", body="body", name="name", language="en"
            ),
        )
        session.post.assert_called_once_with(
            "https://example.org/v3.3/27820001001/message_templates",
            timeout=60,
            json={
                "category": "ACCOUNT_UPDATE",
                "components": json.dumps([{"type": "BODY", "text": "body"}]),
                "name": "name",
                "language": "en",
            },
        )
