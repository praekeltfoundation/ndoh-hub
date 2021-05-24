from __future__ import absolute_import, division

from django.conf import settings
from temba_client.v2 import TembaClient

rapidpro = None
if settings.ADA_RAPIDPRO_URL and settings.ADA_RAPIDPRO_TOKEN:
    rapidpro = TembaClient(settings.ADA_RAPIDPRO_URL, settings.ADA_RAPIDPRO_TOKEN)
