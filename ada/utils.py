from __future__ import absolute_import, division

from django.conf import settings
from temba_client.v2 import TembaClient

rapidpro = None
if settings.ADA_SYMPTOMCHECK_V2:
    rapidpro = TembaClient(settings.RAPIDPRO_URL, settings.RAPIDPRO_TOKEN)
