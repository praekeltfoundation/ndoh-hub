import json
import logging
import asyncio
from datetime import date, datetime, timedelta
import string
from urllib.parse import urljoin
from uuid import UUID
import requests
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import dateparse
from requests.exceptions import RequestException
from temba_client.exceptions import TembaHttpError

from ndoh_hub.celery import app
from ndoh_hub.utils import (
    get_mom_age,
    get_random_date,
    get_today,
    rapidpro,
    send_slack_message,
)
from registrations.models import ClinicCode, JembiSubmission
import time

@app.task(
)
def send_feedback_task(secret_key, inbound_id, feedback_type, **kwargs):

    #for i in range(3):
       # try:
            data = {
                "feedback_secret_key": secret_key,
                "inbound_id": inbound_id,
                "feedback": {"feedback_type": feedback_type},
            }

            if 'faq_id' in kwargs:
                print("Send Feedback On FAQ")
                data["feedback"]["faq_id"] = kwargs.get("faq_id")

            if 'page' in kwargs:
                print("Send Feedback on Page")

                data["feedback"]["page_number"] = kwargs.get("page")
            
            print("Running Send Feedback")
            url = f"{settings.AAQ_CORE_API_URL}/inbound/feedback"

            headers = {
                "Authorization": f"Bearer {settings.AAQ_CORE_API_TOKEN}",
                "Content-Type": "application/json",
            }
            print(data)
            response = requests.request("PUT", url, json=data, headers=headers)
            print("Send Feedback Complete")
            print(f"Response = {response}")
            response.raise_for_status()
            
        #    break
        #except Exception as e:
        #    if i == 2:
        #        print(f"Exception and i = {i}")
        #        return True, {} 
        #    else:
        #        time.sleep(10)   
        #        continue
   #
       