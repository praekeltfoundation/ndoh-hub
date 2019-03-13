"""
This script takes in a CSV on stdin with the fields "name", "language", "content",
which reflects the name of the template, the language that the template is for, as well
as the content of that template.

It then outputs each template in the format expected by the WhatsApp API. If
--execute is set, it submits the template to the WhatsApp API using the authorization
token specified with --token.
"""
import argparse
import csv
import json
import sys
import urllib.parse

import requests

from ndoh_hub.constants import WHATSAPP_LANGUAGE_MAP

WHATSAPP_URL = "https://whatsapp.praekelt.org"
WHATSAPP_TEMPLATE_URL = urllib.parse.urljoin(WHATSAPP_URL, "/v1/message_templates")

session = requests.Session()


def whatsapp_api_format(template):
    """
    Takes a dictionary with name, language, and content keys, and outputs a dictionary
    of the template in the format expected by the whatsapp API.
    """
    return {
        "category": "ALERT_UPDATE",
        "content": template["content"],
        "name": template["name"],
        "language": WHATSAPP_LANGUAGE_MAP[template["language"]],
    }


def submit_to_whatsapp(token, template):
    """
    Submits the template to the WhatsApp API
    """
    r = session.post(
        url=WHATSAPP_TEMPLATE_URL,
        json=template,
        headers={
            "Authorization": "Bearer {}".format(token),
            "Accept": "application/vnd.v1+json",
        },
    )
    r.raise_for_status()


def parse_arguments(args):
    parser = argparse.ArgumentParser(
        description="Submits templates to WhatsApp. Takes a CSV on stdin"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Whether to actually submit template to the WhatsApp API",
    )
    parser.add_argument("--token", help="The token to use for the WhatsApp API")
    return parser.parse_args(args)


def run(input, output, args=None):
    arguments = parse_arguments(args)
    reader = csv.DictReader(input)
    for r in reader:
        template = whatsapp_api_format(r)
        output.write(json.dumps(template))
        output.write("\n")
        if arguments.execute:
            submit_to_whatsapp(arguments.token, template)


if __name__ == "__main__":
    run(sys.stdin, sys.stdout)
