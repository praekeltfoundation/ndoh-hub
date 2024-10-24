import urllib

import requests
from django.conf import settings
from rest_framework import status


def check_urgency_v2(message_text):
    url = urllib.parse.urljoin(settings.AAQ_V2_API_URL, "api/urgency-detect")
    headers = {
        "Authorization": f"Bearer {settings.AAQ_V2_AUTH}",
        "Content-Type": "application/json",
    }

    response = requests.request(
        "POST", url, json={"message_text": message_text}, headers=headers
    )
    response.raise_for_status()

    return response.json()


def search(query_text, generate_llm_response, query_metadata):
    url = urllib.parse.urljoin(settings.AAQ_V2_API_URL, "api/search")
    payload = {
        "query_text": query_text,
        "generate_llm_response": generate_llm_response,
        "query_metadata": query_metadata,
    }
    headers = {
        "Authorization": f"Bearer {settings.AAQ_V2_AUTH}",
        "Content-Type": "application/json",
    }

    response = requests.request("POST", url, json=payload, headers=headers)

    if (
        response.status_code == status.HTTP_400_BAD_REQUEST
        and "detail" in response.json()
    ):
        error_detail = response.json().get("detail", "")
        if "Gibberish text detected" in error_detail:
            return {"message": "Gibberish Detected"}

    response.raise_for_status()

    query_id = response.json()["query_id"]
    feedback_secret_key = response.json()["feedback_secret_key"]
    search_results = response.json()["search_results"]
    json_msg = {}
    body_content = {}
    message_titles = []

    for key, value in enumerate(search_results.values(), start=1):
        text = value["text"]
        id = value["id"]
        title = value["title"]

        body_content[key] = {"text": text, "id": id}
        message_titles.append(f"*{key}* - {title}")

    json_msg = {
        "message": "\n".join(message_titles),
        "body": body_content,
        "feedback_secret_key": feedback_secret_key,
        "query_id": query_id,
    }

    check_urgency_response = check_urgency_v2(query_text)

    json_msg.update(check_urgency_response)

    return json_msg
