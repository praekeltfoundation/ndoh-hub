from django.test import TestCase
from django.urls import reverse

from .models import RedirectUrl


class TestViews(TestCase):
    def test_whatsapp_url_error(self):
        """
        Should check that the right template is used for no whatsapp string in url
        """
        response = self.client.get("https://hub.momconnect.za/redirect/52?")
        self.assertTemplateUsed(response, "index.html")

    def test_name_error(self):
        """
        Should check that the right template formisspelt whatsappid
        """
        response = self.client.get(
            "https://hub.momconnect.za/redirect/52?whatsappi=12345"
        )
        self.assertTemplateUsed(response, "index.html")

    def test_name_success(self):
        """
        Should use the meta refresh template if url is correct
        """
        response = self.client.get(
            "https://hub.momconnect.za/redirect/52?whatsappid=12345"
        )
        self.assertTemplateUsed(response, "meta_refresh.html")


class AdaHookViewTests(TestCase):
    def setUp(self):
        super(AdaHookViewTests, self).setUp()
        self.post = RedirectUrl.objects.create(
            url="https://hub.momconnect.za/confirmredirect",
            content="Entry has no copy",
            symptom_check_url="http://symptomcheck.co.za",
            parameter="1",
            time_stamp="2021-05-06 07:24:14.014990+00:00",
        )

    def tearDown(self):
        super(AdaHookViewTests, self).tearDown()
        self.post.delete()

    def test_ada_hook_redirect_success(self):
        response = self.client.get(
            reverse("ada_hook_redirect", args=(self.post.id, self.post.id))
        )
        self.assertEqual(response.status_code, 302)

    def test_ada_hook_redirect_404(self):
        response = self.client.get(reverse("ada_hook_redirect", args=("1", "1")))
        self.assertEqual(response.status_code, 404)
