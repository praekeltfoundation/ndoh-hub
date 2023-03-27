import uuid

from django.contrib.auth.models import User
from django.db import models
from simple_history.models import HistoricalRecords


class Source(models.Model):
    """The source from which a registation originates.
    The User foreignkey is used to identify the source based on the
    user's api token.
    """

    AUTHORITY_CHOICES = (
        ("patient", "Patient"),
        ("advisor", "Trusted Advisor"),
        ("hw_partial", "Health Worker Partial"),
        ("hw_full", "Health Worker Full"),
    )
    name = models.CharField(max_length=100, null=False, blank=False)
    user = models.ForeignKey(
        User, related_name="sources", null=False, on_delete=models.CASCADE
    )
    authority = models.CharField(
        max_length=30, null=False, blank=False, choices=AUTHORITY_CHOICES
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s" % self.name


class Registration(models.Model):
    """A registation submitted via Vumi or other sources.

    After a registation has been created, a task will fire that
    validates if the data provided is sufficient for the type
    of pregnancy.

    Args:
        reg_type (str): The type of registration
        data (json): Registration info in json format
        validated (bool): True if the registation has been
            validated after creation
        source (object): Auto-completed field based on the Api key
    """

    REG_TYPE_CHOICES = (
        ("momconnect_prebirth", "MomConnect pregnancy registration"),
        ("momconnect_postbirth", "MomConnect baby registration"),
        ("whatsapp_prebirth", "WhatsApp MomConnect pregnancy registration"),
        ("whatsapp_postbirth", "WhatsApp MomConnect baby registration"),
        ("nurseconnect", "Nurseconnect registration"),
        ("whatsapp_nurseconnect", "WhatsApp Nurseconnect registration"),
        ("pmtct_prebirth", "PMTCT pregnancy registration"),
        ("whatsapp_pmtct_prebirth", "WhatsApp PMTCT pregnancy registration"),
        ("pmtct_postbirth", "PMTCT baby registration"),
        ("whatsapp_pmtct_postbirth", "WhatsApp PMTCT baby registration"),
        ("loss_general", "Loss general registration"),
        (
            "jembi_momconnect",
            "Jembi MomConnect registration. Set temporarily "
            "until we calculate which registration it should be",
        ),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_id = models.CharField(
        unique=True,
        blank=True,
        null=True,
        db_index=True,
        default=None,
        max_length=100,
        help_text="The ID of the registration in the external "
        "service that created the registration",
    )
    reg_type = models.CharField(
        max_length=30, null=False, blank=False, choices=REG_TYPE_CHOICES
    )
    registrant_id = models.CharField(
        max_length=36, null=True, blank=False, db_index=True
    )
    data = models.JSONField(null=True, blank=True)
    validated = models.BooleanField(default=False)
    source = models.ForeignKey(
        Source, related_name="registrations", null=False, on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User, related_name="registrations_created", null=True, on_delete=models.SET_NULL
    )
    updated_by = models.ForeignKey(
        User, related_name="registrations_updated", null=True, on_delete=models.SET_NULL
    )
    user = property(lambda self: self.created_by)

    def __str__(self):
        return str(self.id)

    def get_subscription_requests(self):
        """
        Returns all possible subscriptions created for this registration.

        :returns: Django Queryset
        """
        return SubscriptionRequest.objects.filter(identity=self.registrant_id)

    @property
    def status(self):
        """
        Returns the processing status information for the registration
        """
        from registrations.serializers import RegistrationSerializer

        data = {
            "registration_id": str(self.external_id or self.id),
            "registration_data": RegistrationSerializer(instance=self).data,
        }

        if self.validated is True:
            data["status"] = "succeeded"
        elif "invalid_fields" in self.data:
            data["status"] = "validation_failed"
            data["error"] = self.data["invalid_fields"]
        elif "error_data" in self.data:
            data["status"] = "failed"
            data["error"] = self.data["error_data"]
        else:
            data["status"] = "processing"
        return data

    class Meta:
        permissions = [
            ("subscription_check_registration", "Can perform a subscription check")
        ]


class SubscriptionRequest(models.Model):
    """A data model that maps to the Stagebased Store
    Subscription model. Created after a successful Registration
    validation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.CharField(max_length=36, null=False, blank=False)
    messageset = models.IntegerField(null=False, blank=False)
    next_sequence_number = models.IntegerField(default=1, null=False, blank=False)
    lang = models.CharField(max_length=6, null=False, blank=False)
    schedule = models.IntegerField(default=1)
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def serialize_hook(self, hook):
        # optional, there are serialization defaults
        # we recommend always sending the Hook
        # metadata along for the ride as well
        return {
            "hook": hook.dict(),
            "data": {
                "id": str(self.id),
                "identity": self.identity,
                "messageset": self.messageset,
                "next_sequence_number": self.next_sequence_number,
                "lang": self.lang,
                "schedule": self.schedule,
                "metadata": self.metadata,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat(),
            },
        }

    def __str__(self):
        return str(self.id)


class PositionTracker(models.Model):
    """
    Tracks the position that we want a certain message set to be on. This is a
    bit of a hack for messagesets where we want everyone to be in the same
    position in the message set.

    This gets incremented when the send happens, and all new registrations
    look here to see where in the message set to place the new subscriptions.
    """

    label = models.CharField(
        max_length=100,
        null=False,
        blank=False,
        primary_key=True,
        help_text="The unique label to identify the tracker",
    )
    position = models.IntegerField(
        default=1, help_text="The current position of the tracker"
    )
    history = HistoricalRecords()

    class Meta:
        permissions = (
            ("increment_position_positiontracker", "Can increment the position"),
        )

    @property
    def modified_at(self):
        """
        Returns the datetime when the position was last modified
        """
        return self.history.first().history_date

    def __str__(self):
        return "{}: {}".format(self.label, self.position)


class WhatsAppContact(models.Model):
    """
    Caches the results of the WhatsApp contact check
    """

    msisdn = models.CharField(max_length=100, help_text="The MSISDN of the contact")
    whatsapp_id = models.CharField(
        max_length=100, blank=True, help_text="The WhatsApp ID of the contact"
    )
    created = models.DateTimeField(auto_now_add=True)

    @property
    def api_format(self):
        if self.whatsapp_id:
            return {"input": self.msisdn, "status": "valid", "wa_id": self.whatsapp_id}
        return {"input": self.msisdn, "status": "invalid"}

    class Meta:
        permissions = (("can_prune_whatsappcontact", "Can prune WhatsApp contact"),)
        verbose_name = "WhatsApp Contact"
        indexes = [models.Index(fields=["msisdn"])]


class ClinicCode(models.Model):
    code = models.CharField(max_length=255)
    value = models.CharField(max_length=255)
    uid = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    province = models.CharField(max_length=6, blank=True, null=True, default=None)
    location = models.CharField(max_length=255, blank=True, null=True, default=None)

    class Meta:
        indexes = [models.Index(fields=["value"])]


class JembiSubmission(models.Model):
    path = models.CharField(max_length=255)
    request_data = models.JSONField()
    timestamp = models.DateTimeField(auto_now_add=True)
    submitted = models.BooleanField(default=False)
    response_status_code = models.IntegerField(null=True, default=None)
    response_headers = models.JSONField(default=dict)
    response_body = models.TextField(blank=True, default="")
