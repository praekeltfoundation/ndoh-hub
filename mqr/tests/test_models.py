from django.test import TestCase

from mqr.models import MqrStrata


class MqrStrataTests(TestCase):
    def test_strata_arm_insert(self):
        """
        Checks if the record inserted
        """

        strata_arm = MqrStrata.objects.create(
            province="Kzn",
            weeks_pregnant="<=13",
            age=22,
            next_index=1,
            order="RCM,BCM,ARM,RCM_SMS,RCM_BCM",
        )
        get_arm = MqrStrata.objects.get(province="Kzn", weeks_pregnant="<=13", age="22")

        strata, created = MqrStrata.objects.get_or_create(
            province="Kzn", weeks_pregnant="<=13", age=22
        )

        self.assertEqual(strata_arm.id, get_arm.id)
        self.assertNotEqual(created, True)
        self.assertIsNotNone(strata)

    def test_get_or_create_strata_arm(self):
        strata_arm = MqrStrata.objects.create(
            province="WC",
            weeks_pregnant="21-27",
            age=34,
            next_index=2,
            order="RCM_BCM,ARM,RCM,RCM_SMS,BCM",
        )

        strata, created = MqrStrata.objects.get_or_create(
            province="WC", weeks_pregnant="21-27", age=35
        )

        self.assertNotEqual(strata_arm.id, strata.id)
        self.assertIsNotNone(strata)
        self.assertTrue(created)
