from urllib.parse import urljoin

import requests

MSISDN_FILENAME = "users.csv"
TURN_URL = "https://whatsapp.turn.io/"
TURN_TOKEN = (
    "eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiJFbmdhZ2VkIiwiZXhwIjoxNjQ1MjgyMjAyL"
    "CJpYXQiOjE2MTM3NDYyMDYsImlzcyI6IkVuZ2FnZWQiLCJqdGkiOiJiNjdhMWE1Ny05ODQ3LTQ0NzEtYjd"
    "hMy0yM2VhODcxNGE0YTYiLCJuYmYiOjE2MTM3NDYyMDUsInN1YiI6Im51bWJlcjo1NzciLCJ0eXAiOiJhY"
    "2Nlc3MifQ.Ca7sTR1rzZTZOwjxKWxKk1Gc1CFAiDhZqeOUpjM4TU0DTgXiqhv9opd_NGxlC621ueGuxjBl"
    "Jx85hzqyoeGG1w"
)
RAPIDPRO_URL = "https://healthcheck-rapidpro.ndoh-k8s.prd-p6t.org/"
RAPIDPRO_TOKEN = "33a48e89184ab9895ebd8bae8f745e972c237f50"
RAPIDPRO_FLOW = "782cba45-7367-4a05-a9cd-b852aa9d8c92"

with open("users.csv") as f:
    for msisdn in f:
        msisdn = msisdn.lstrip("+").strip()
        r = requests.patch(
            url=urljoin(TURN_URL, f"/v1/contacts/{msisdn}/profile"),
            headers={
                "Authorization": f"Bearer {TURN_TOKEN}",
                "Accept": "application/vnd.v1+json",
            },
            json={"existing_user": True},
        )
        r.raise_for_status()
        r = requests.post(
            url=urljoin(RAPIDPRO_URL, "/api/v2/flow_starts.json"),
            headers={"Authorization": f"Token {RAPIDPRO_TOKEN}"},
            json={"flow": RAPIDPRO_FLOW, "urns": [f"whatsapp:{msisdn}"]},
        )
        r.raise_for_status()
        print(msisdn)
