import argparse
from urllib.parse import urlencode, urljoin

import requests


def get_arguments():
    parser = argparse.ArgumentParser(
        description="Fetches all the whatsapp IDs of a group of contacts"
    )
    parser.add_argument(
        "--url",
        help="The base URL for the rapidpro instance",
        default="https://rapidpro.prd.momconnect.co.za/",
    )
    parser.add_argument("token", help="Authorization token for RapidPro")
    parser.add_argument("group", help="The group to fetch contacts for")
    return parser.parse_args()


def format_urn(urn: str):
    _, path = urn.split(":")
    return path


def fetch_contacts(url, token, group):
    url = urljoin(url, "/api/v2/contacts.json")
    query = urlencode({"group": group})
    next_ = f"{url}?{query}"

    while next_:
        response = requests.get(
            next_,
            headers={"Authorization": f"Token {token}", "Accept": "application/json"},
        )
        response.raise_for_status()
        result = response.json()
        next_ = result["next"]
        for contact in result["results"]:
            if contact["urns"]:
                print(format_urn(contact["urns"][0]))


def main():
    args = get_arguments()
    fetch_contacts(args.url, args.token, args.group)


if __name__ == "__main__":
    main()
