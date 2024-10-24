import argparse
import json
from csv import DictReader
from urllib.parse import urljoin

import attr
import requests


def length_limit(limit):
    def validate_length(instance, attribute, value):
        if len(value) > limit:
            raise ValueError(
                f"{attribute.name} must be shorter or equal to {limit} characters"
            )

    return validate_length


@attr.s
class Template:
    category = attr.ib(
        validator=attr.validators.in_(
            (
                "ACCOUNT_UPDATE",
                "PAYMENT_UPDATE",
                "PERSONAL_FINANCE_UPDATE",
                "SHIPPING_UPDATE",
                "RESERVATION_UPDATE",
                "ISSUE_RESOLUTION",
                "APPOINTMENT_UPDATE",
                "TRANSPORTATION_UPDATE",
                "TICKET_UPDATE",
                "ALERT_UPDATE",
                "AUTO_REPLY",
            )
        )
    )
    # Note: We don't require a header or footer, so it's not included here
    body = attr.ib(validator=(attr.validators.instance_of(str), length_limit(1024)))
    name = attr.ib(validator=attr.validators.instance_of(str))
    # Note: These are not all the languages, just the ones that are relevant to
    # MomConnect. The full set of supported languages can be found at
    # https://developers.facebook.com/docs/whatsapp/business-management-api/message-templates#creating-message-templates
    language = attr.ib(validator=attr.validators.in_(("en", "af")))


def parse_templates(args):
    return [
        Template(
            category=d[args.category],
            body=d[args.body],
            name=d[args.name],
            language=d[args.language],
        )
        for d in DictReader(args.csv_file)
    ]


def submit_template(args, session, template):
    data = {
        "category": template.category,
        # This API requires the components to be double JSON encoded
        "components": json.dumps([{"type": "BODY", "text": template.body}]),
        "name": template.name.lower(),
        "language": template.language,
    }
    response = session.post(
        urljoin(args.base_url, f"v3.3/{args.number}/message_templates"),
        timeout=60,
        json=data,
    )
    try:
        response.raise_for_status()
    except requests.RequestException:
        print("URL: ", urljoin(args.base_url, f"v3.3/{args.number}/message_templates"))
        print("Body: ", data)
        print("Response code: ", response.status_code)
        print("Response body: ", response.json())
        return {"id": None}
    return response.json()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Uploads templates to WhatsApp")
    parser.add_argument("csv_file", help="The CSV containing the templates", type=open)
    parser.add_argument("number", help="the whatsapp number of the account")
    parser.add_argument(
        "-u",
        "--base-url",
        help="The base URL for the API, default https://whatsapp.praekelt.org",
        default="https://whatsapp.praekelt.org",
    )
    parser.add_argument(
        "-c",
        "--category",
        help="The column name containing the category, default template_type",
        default="template_type",
    )
    parser.add_argument(
        "-b",
        "--body",
        help="The column name containing the body, default content",
        default="content",
    )
    parser.add_argument(
        "-n",
        "--name",
        help="The column name containing the name, default template_name",
        default="template_name",
    )
    parser.add_argument(
        "-l",
        "--language",
        help="The column name containing the language, default language",
        default="language",
    )
    args = parser.parse_args()

    templates = parse_templates(args)

    token = input("Authorization token? ")
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "NDOH-Hub/CLI", "Authorization": f"Bearer {token}"}
    )

    for template in templates:
        print(f"Submitting template {template.name} {template.language}")
        result = submit_template(args, session, template)
        print(f"Created template {result['id']}\n")
