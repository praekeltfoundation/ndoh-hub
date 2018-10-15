import uuid

from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.utils.encoding import python_2_unicode_compatible

from registrations.models import Source


@python_2_unicode_compatible
class Change(models.Model):
    """ A request to change a subscription

    Args:
        registrant_id (str): UUID of the registrant's identity
        action (str): What type of change to implement
        data (json): Change info in json format
        source (object): Auto-completed field based on the Api key
    """

    ACTION_CHOICES = (
        ("baby_switch", "Change from pregnancy to baby messaging"),
        ("pmtct_loss_switch", "Change to loss messaging via pmtct app"),
        ("pmtct_loss_optout", "Optout due to loss via pmtct app"),
        ("pmtct_nonloss_optout", "Optout not due to loss via pmtct app"),
        ("nurse_update_detail", "Update nurseconnect detail"),
        ("nurse_change_msisdn", "Change nurseconnect msisdn"),
        ("nurse_optout", "Optout from nurseconnect"),
        ("momconnect_loss_switch", "Change to loss messaging via momconnect app"),
        ("momconnect_loss_optout", "Optout due to loss via momconnect app"),
        ("momconnect_nonloss_optout", "Optout not due to loss via momconnect app"),
        (
            "momconnect_change_language",
            "Change the language of the messages via momconnect app",
        ),
        (
            "momconnect_change_msisdn",
            "Change the MSISDN to send messages to via momconnect app",
        ),
        (
            "momconnect_change_identification",
            "Change the identification type and number via momconnect app",
        ),
        (
            "admin_change_subscription",
            "Change the message set and/or language of the specified "
            "subscription from admin",
        ),
        (
            "switch_channel",
            "Switch which channel (eg. SMS, WhatsApp) to receive messages on",
        ),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registrant_id = models.CharField(max_length=36, null=False, blank=False)
    action = models.CharField(
        max_length=255, null=False, blank=False, choices=ACTION_CHOICES
    )
    data = JSONField(null=True, blank=True)
    validated = models.BooleanField(default=False)
    source = models.ForeignKey(
        Source, related_name="changes", null=True, on_delete=models.SET_NULL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, related_name="changes_created", null=True, on_delete=models.SET_NULL
    )
    updated_by = models.ForeignKey(
        User, related_name="changes_updated", null=True, on_delete=models.SET_NULL
    )
    user = property(lambda self: self.created_by)

    def __str__(self):
        return str(self.id)
