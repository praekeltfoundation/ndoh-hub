import argparse
import sys
from urllib.parse import urljoin

import requests


def get_arguments():
    parser = argparse.ArgumentParser(
        description="Updates a contact field in Turn for all whatsapp IDs on stdin"
    )
    parser.add_argument(
        "--url",
        help="The base URL for the Turn instance",
        default="https://whatsapp-praekelt-cloud.turn.io/",
    )
    parser.add_argument("token", help="Authorization token for Turn")
    parser.add_argument("field", help="The contact field to set")
    parser.add_argument("value", help="The value to set the contact field to")
    return parser.parse_args()


def update_contact(url, token, field, value, whatsapp_id):
    url = urljoin(url, f"/v1/contacts/{whatsapp_id}/profile")
    response = requests.patch(
        url,
        json={field: value},
        headers={
            "Accept": "application/vnd.v1+json",
            "Authorization": f"Bearer {token}",
        },
    )
    if not response.ok:
        print(f"Error updating {whatsapp_id}")
        print(response.status_code)
        print(response.text)
    else:
        print(f"Updated {whatsapp_id}")


def main():
    args = get_arguments()
    for line in sys.stdin:
        update_contact(args.url, args.token, args.field, args.value, line.strip())


if __name__ == "__main__":
    main()
