from django.test import SimpleTestCase
from django.urls import resolve, reverse

from ada.views import clickActivity, default_page


class TestUrls(SimpleTestCase):
    def test_ada_hook_redirect_is_resolved(self):
        url = reverse("ada_hook_redirect", args=["1", "1"])
        self.assertEqual(resolve(url).func, clickActivity)

    def test_ada_hook_is_resolved(self):
        url = reverse("ada_hook", args=["1"])
        self.assertEqual(resolve(url).func, default_page)
