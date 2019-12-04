from celery.exceptions import SoftTimeLimitExceeded
from requests.exceptions import RequestException

from ndoh_hub.celery import app
from ndoh_hub.utils import rapidpro


@app.task(
    autoretry_for=(RequestException, SoftTimeLimitExceeded),
    retry_backoff=True,
    max_retries=15,
    acks_late=True,
    soft_time_limit=10,
    time_limit=15,
)
def async_create_flow_start(extra, **kwargs):
    return rapidpro.create_flow_start(extra=extra, **kwargs)
