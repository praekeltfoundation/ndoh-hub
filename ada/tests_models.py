from django.test import TestCase
from freezegun import freeze_time

from .models import RedirectUrl, RedirectUrlsEntry


class TestAppModels(TestCase):
    def test_RedirectUrl(self):
        parameter = RedirectUrl.objects.create(parameter=1)
        self.assertEqual(
            str(parameter),
            "1: https://hub.momconnect.za/confirmredirect/1 \n"
            "| Clicked 0 times | Content: This entry has no copy",
        )

    @freeze_time("2021-05-06 07:24:14.014990+00:00")
    def test_RedirectUrlsEntry(self):
        urls = RedirectUrl.objects.create(
            url="https://hub.momconnect.za/confirmredirect"
        )
        url = RedirectUrlsEntry.objects.create(url=urls)
        self.assertEqual(
            str(url),
            "https://hub.momconnect.za/confirmredirect with ID 2 \n"
            "was visited at 2021-05-06 07:24:14.014990+00:00",
        )
