from django.test import TestCase

from registrations.models import Registration


class RegistrationTests(TestCase):
    def test_registration_status_external_id(self):
        """
        If there is an external ID set, then the returned ID should be the
        external ID, otherwise it should be the model's ID.
        """
        reg = Registration(external_id="test-external", data={})
        self.assertEqual(reg.status["registration_id"], "test-external")

        reg = Registration(data={})
        self.assertEqual(reg.status["registration_id"], str(reg.id))

    def test_registration_status_succeeded(self):
        """
        If validated=True, then the status should be succeeded
        """
        reg = Registration(validated=True)
        self.assertEqual(reg.status["status"], "succeeded")

    def test_registration_status_validation_failed(self):
        """
        If validated=False, and there are invalid_fields in the data, then
        the status should be validation_failed, and the error should be the
        invalid fields
        """
        invalid_fields = {"test-field": "Test reason"}
        reg = Registration(data={"invalid_fields": invalid_fields})
        self.assertEqual(reg.status["status"], "validation_failed")
        self.assertEqual(reg.status["error"], invalid_fields)

    def test_registration_status_failed(self):
        """
        If validated=False, and there is error_data in the data, then the
        status should be failed, and the error should be the error data
        """
        error_data = {"test-error": "error-data"}
        reg = Registration(data={"error_data": error_data})
        self.assertEqual(reg.status["status"], "failed")
        self.assertEqual(reg.status["error"], error_data)

    def test_registration_status_processing(self):
        """
        If validated=False, but there is no error data in data, then the status
        should be processing
        """
        reg = Registration(data={})
        self.assertEqual(reg.status["status"], "processing")
