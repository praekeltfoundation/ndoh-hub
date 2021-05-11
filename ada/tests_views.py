from urllib.parse import urljoin

from django.test import TestCase
from django.urls import reverse

from .models import RedirectUrl


class TestViews(TestCase):
    def test_whatsapp_url_error(self):
        """
        Should check that the right template is used for no whatsapp string in url
        """
        response = self.client.get(reverse("ada_hook", args=["1"]))
        self.assertTemplateUsed(response, "index.html")

    def test_name_error(self):
        """
        Should check that the right template is used for mis-spelt whatsappid
        """
        qs = "?whatsappi=12345"
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "index.html")

    def test_no_whatsapp_value(self):
        """
        Should check that the right template is used if there's no whatsapp value
        """
        qs = "?whatsapp="
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "index.html")

    def test_no_query_string(self):
        """
        Should check that the right template is used if there's no whatsapp value
        """
        qs = "?"
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "index.html")

    def test_name_success(self):
        """
        Should use the meta refresh template if url is correct
        """
        qs = "?whatsappid=12345"
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "meta_refresh.html")

    def test_special_character(self):
        """
        Should use the meta refresh template if url is correct
        """
        qs = "?whatsappid=12@45"
        url = urljoin(reverse("ada_hook", args=["1"]), qs)
        response = self.client.get(url)
        self.assertTemplateUsed(response, "index.html")


class AdaHookViewTests(TestCase):
    def setUp(self):
        super(AdaHookViewTests, self).setUp()
        self.post = RedirectUrl.objects.create(
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
            reverse("ada_hook_redirect", args=(self.post.id, "1235"))
        )
        self.assertEqual(response.status_code, 302)

    # Raise HTTp404 if RedirectUrl does not exist
    def test_ada_hook_redirect_404(self):
        response = self.client.get(
            reverse("ada_hook_redirect", args=("1", "27789049372"))
        )
        self.assertEqual(response.status_code, 404)

    # Raise HTTp404 if ValueError
    def test_ada_hook_redirect_404_nameError(self):
        response = self.client.get(
            reverse("ada_hook_redirect", args=("invalidurlid", "invalidwhatsappid"))
        )
        self.assertEqual(response.status_code, 404)
