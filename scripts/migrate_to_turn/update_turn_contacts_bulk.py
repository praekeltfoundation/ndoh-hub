import os
import sys
from urllib.parse import urljoin

import requests

TURN_URL = "https://whatsapp-praekelt-cloud.turn.io"


def bulk_update_turn_contacts(filename):
    data = open(filename, "rb")
    url = urljoin(TURN_URL, "v1/contacts")
    headers = {
        "Authorization": f"Bearer {os.environ['TURN_TOKEN']}",
        "content-type": "text/csv",
    }
    response = requests.post(url, data=data, headers=headers)

    print(response.status_code)

    f = open(f"result_{filename}", "wb")
    f.write(response.content)
    f.close()


if __name__ == "__main__":
    filename = sys.argv[1]
    bulk_update_turn_contacts(filename)
