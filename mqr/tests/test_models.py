from django.test import TestCase

from mqr.models import MqrStrata


class MqrStrataTests(TestCase):
    def test_strata_arm_insert(self):
        """
        Checks if the record inserted
        """

        strata_arm = MqrStrata.objects.create(
            province="Kzn",
            weeks_pregnant_bucket="16-20",
            age_bucket="31+",
            next_index=1,
            order="RCM,BCM,ARM,RCM_SMS,RCM_BCM",
        )
        get_arm = MqrStrata.objects.get(
            province="Kzn", weeks_pregnant_bucket="16-20", age_bucket="31+"
        )

        strata, created = MqrStrata.objects.get_or_create(
            province="Kzn", weeks_pregnant_bucket="16-20", age_bucket="31+"
        )

        self.assertEqual(strata_arm.id, get_arm.id)
        self.assertNotEqual(created, True)
        self.assertIsNotNone(strata)

    def test_get_or_create_strata_arm(self):
        strata_arm = MqrStrata.objects.create(
            province="WC",
            weeks_pregnant_bucket="21-27",
            age_bucket="18-30",
            next_index=2,
            order="RCM_BCM,ARM,RCM,RCM_SMS,BCM",
        )

        strata, created = MqrStrata.objects.get_or_create(
            province="WC", weeks_pregnant_bucket="21-27", age_bucket="30+"
        )

        self.assertNotEqual(strata_arm.id, strata.id)
        self.assertIsNotNone(strata)
        self.assertTrue(created)
