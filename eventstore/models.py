import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils import timezone


class OptOut(models.Model):
    STOP_TYPE = "stop"
    FORGET_TYPE = "forget"
    LOSS_TYPE = "loss"
    OPTOUT_TYPES = ((STOP_TYPE, "Stop"), (FORGET_TYPE, "Forget"), (LOSS_TYPE, "Loss"))

    NOT_USEFUL_REASON = "not_useful"
    OTHER_REASON = "other"
    UNKNOWN_REASON = "unknown"
    SMS_FAILURE_REASON = "sms_failure"
    MISCARRIAGE_REASON = "miscarriage"
    STILLBIRTH_REASON = "stillbirth"
    BABYLOSS_REASON = "babyloss"
    NOT_HIV_POSITIVE_REASON = "not_hiv_pos"
    REASON_TYPES = (
        (NOT_USEFUL_REASON, "Not useful"),
        (OTHER_REASON, "Other"),
        (UNKNOWN_REASON, "Unknown"),
        (SMS_FAILURE_REASON, "SMS failure"),
        (MISCARRIAGE_REASON, "Miscarriage"),
        (STILLBIRTH_REASON, "Stillbirth"),
        (BABYLOSS_REASON, "Lost baby"),
        (NOT_HIV_POSITIVE_REASON, "Not HIV positive"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    optout_type = models.CharField(max_length=6, choices=OPTOUT_TYPES)
    reason = models.CharField(max_length=11, choices=REASON_TYPES)
    source = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    data = JSONField(default=dict, blank=True, null=True)

    def __str__(self):
        return "{} opt out: {} <{}>".format(
            self.get_optout_type_display(), self.get_reason_display(), self.contact_id
        )


class BabySwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    data = JSONField(default=dict, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Baby switches"


class ChannelSwitch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    source = models.CharField(max_length=255)
    from_channel = models.CharField(max_length=255)
    to_channel = models.CharField(max_length=255)
    timestamp = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    data = JSONField(default=dict, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Channel switches"
