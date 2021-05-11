from django.test import TestCase
from freezegun import freeze_time

from .models import RedirectUrl, RedirectUrlsEntry


class TestAppModels(TestCase):
    def test_RedirectUrl(self):
        parameter = RedirectUrl.objects.create(parameter=1)
        self.assertEqual(
            str(parameter),
            "1: https://hub.momconnect.co.za/redirect/1 \n"
            "| Clicked 0 times | Content: This entry has no copy",
        )

    @freeze_time("2021-05-06 07:24:14.014990+00:00")
    def test_RedirectUrlsEntry(self):
        urls = RedirectUrl.objects.create(symptom_check_url="http://symptomcheck.co.za")
        url = RedirectUrlsEntry.objects.create(symptom_check_url=urls)
        self.assertEqual(
            str(url),
            "https://hub.momconnect.co.za/redirect with parameter \n"
            "None \nwas visited at 2021-05-06 07:24:14.014990+00:00",
        )
