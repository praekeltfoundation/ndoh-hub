import datetime
import six  # for Python 2 and 3 string type compatibility
import requests
import json
import uuid

from django.conf import settings
from celery.task import Task
from celery.utils.log import get_task_logger

from .models import Registration


logger = get_task_logger(__name__)


def is_valid_date(date):
    try:
        datetime.datetime.strptime(date, "%Y%m%d")
        return True
    except:
        return False


def is_valid_uuid(id):
    return len(id) == 36 and id[14] == '4' and id[19] in ['a', 'b', '8', '9']


def is_valid_lang(lang):
    return lang in ["eng_ZA"]


def is_valid_msg_type(msg_type):
    return msg_type in ["text"]  # currently text only


def is_valid_msg_receiver(msg_receiver):
    return msg_receiver in ["mother_to_be"]


def is_valid_loss_reason(loss_reason):
    return loss_reason in ["miscarriage"]


def is_valid_name(name):
    return isinstance(name, six.string_types)  # TODO reject non-letters


def is_valid_id_type(id_type):
    return id_type in ["sa_id"]


def is_valid_id_no(id_no):
    return isinstance(id_no, six.string_types)  # TODO proper id validation


class ValidateRegistration(Task):
    """ Task to validate a registration model entry's registration
    data.
    """
    name = "ndoh_hub.registrations.tasks.validate_registration"

    def check_field_values(self, fields, registration_data):
        failures = []
        for field in fields:
            pass
        return failures

    def validate(self, registration):
        """ Validates that all the required info is provided for a
        prebirth registration.
        """
        return True

    def create_subscriptionrequests(self, registration):
        """ Create SubscriptionRequest(s) based on the
        validated registration.
        """

        # Create subscription
        return "SubscriptionRequest created"

    def run(self, registration_id, **kwargs):
        """ Sets the registration's validated field to True if
        validation is successful.
        """
        l = self.get_logger(**kwargs)
        l.info("Looking up the registration")
        registration = Registration.objects.get(id=registration_id)
        reg_validates = self.validate(registration)

        validation_string = "Validation completed - "
        if reg_validates:
            validation_string += "Success"
            self.create_subscriptionrequests(registration)
        else:
            validation_string += "Failure"

        return validation_string

validate_registration = ValidateRegistration()


class DeliverHook(Task):
    def run(self, target, payload, instance_id=None, hook_id=None, **kwargs):
        """
        target:     the url to receive the payload.
        payload:    a python primitive data structure
        instance_id:   a possibly None "trigger" instance ID
        hook_id:       the ID of defining Hook object
        """
        requests.post(
            url=target,
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'Authorization': 'Token %s' % settings.HOOK_AUTH_TOKEN
            }
        )


def deliver_hook_wrapper(target, payload, instance, hook):
    if instance is not None:
        if isinstance(instance.id, uuid.UUID):
            instance_id = str(instance.id)
        else:
            instance_id = instance.id
    else:
        instance_id = None
    kwargs = dict(target=target, payload=payload,
                  instance_id=instance_id, hook_id=hook.id)
    DeliverHook.apply_async(kwargs=kwargs)
