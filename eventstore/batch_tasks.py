from celery_batches import Batches
from django.conf import settings

from eventstore.models import Event
from eventstore.whatsapp_actions import handle_event
from ndoh_hub.celery import app


@app.task(base=Batches, flush_every=100, flush_interval=10)
def bulk_insert_events(requests):
    data = []
    for request in requests:
        data.append(Event(**request.kwargs))

    events = Event.objects.bulk_create(data)
    if settings.ENABLE_EVENTSTORE_WHATSAPP_ACTIONS:
        for event in events:
            handle_event(event)
