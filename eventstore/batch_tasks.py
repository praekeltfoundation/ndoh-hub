import logging

from celery_batches import Batches
from django.conf import settings

from eventstore.models import Event
from eventstore.whatsapp_actions import handle_event
from ndoh_hub.celery import app

logger = logging.getLogger(__name__)


@app.task(
    base=Batches,
    flush_every=settings.BULK_INSERT_EVENTS_FLUSH_EVERY,
    flush_interval=settings.BULK_INSERT_EVENTS_FLUSH_INTERVAL,
    acks_late=True,
)
def bulk_insert_events(requests):
    logger.info(f">>> bulk_insert_events: {len(requests)}")
    data = []
    for request in requests:
        data.append(Event(**request.kwargs))

    events = Event.objects.bulk_create(data)
    if settings.ENABLE_EVENTSTORE_WHATSAPP_ACTIONS:
        for event in events:
            handle_event(event)
