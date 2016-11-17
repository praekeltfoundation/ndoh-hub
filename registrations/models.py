import uuid

from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.encoding import python_2_unicode_compatible

from ndoh_hub import utils


@python_2_unicode_compatible
class Source(models.Model):
    """ The source from which a registation originates.
        The User foreignkey is used to identify the source based on the
        user's api token.
    """
    AUTHORITY_CHOICES = (
        ('patient', "Patient"),
        ('advisor', "Trusted Advisor"),
        ('hw_limited', "Health Worker Limited"),
        ('hw_full', "Health Worker Full")
    )
    name = models.CharField(max_length=100, null=False, blank=False)
    user = models.ForeignKey(User, related_name='sources', null=False)
    authority = models.CharField(max_length=30, null=False, blank=False,
                                 choices=AUTHORITY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "%s" % self.name


@python_2_unicode_compatible
class Registration(models.Model):
    """ A registation submitted via Vumi or other sources.

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
        ('momconnect_prebirth', "MomConnect pregnancy registration"),
        ('momconnect_postbirth', "MomConnect baby registration"),
        ('nurseconnect', "Nurseconnect registration"),
        ('pmtct_prebirth', "PMTCT pregnancy registration"),
        ('pmtct_postbirth', "PMTCT baby registration"),
        ('loss_general', "Loss general registration"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reg_type = models.CharField(max_length=30, null=False, blank=False,
                                choices=REG_TYPE_CHOICES)
    registrant_id = models.CharField(max_length=36, null=False, blank=False)
    data = JSONField(null=True, blank=True)
    validated = models.BooleanField(default=False)
    source = models.ForeignKey(Source, related_name='registrations',
                               null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, related_name='registrations_created',
                                   null=True, blank=True)
    updated_by = models.ForeignKey(User, related_name='registrations_updated',
                                   null=True, blank=True)
    user = property(lambda self: self.created_by)

    def __str__(self):
        return str(self.id)

    def _check_registrant_id(self):
        if not utils.is_valid_uuid(self.registrant_id):
            self.v.append("Invalid UUID: registrant_id")

    def _check_reg_type(self):
        if self.reg_type not in [i[0] for i in self.REG_TYPE_CHOICES]:
            self.v.append("Invalid choice: reg_type")

    def _check_operator_id(self):
        if not utils.is_valid_uuid(self.data["operator_id"]):
            self.v.append("Invalid UUID: operator_id")

    def _check_msisdn_registrant(self):
        if not utils.is_valid_msisdn(self.data["msisdn_registrant"]):
            self.v.append("Invalid MSISDN: msisdn_registrant")

    def _check_msisdn_device(self):
        if not utils.is_valid_msisdn(self.data["msisdn_device"]):
            self.v.append("Invalid MSISDN: msisdn_device")

    def _check_sa_id_no(self):
        if not utils.is_valid_sa_id_no(self.data["sa_id_no"]):
            self.v.append("Invalid SA ID number: sa_id_no")

    def _check_mom_dob(self):
        if not utils.is_valid_date(self.data["mom_dob"]):
            self.v.append("Invalid date: mom_dob")

    def _check_passport_no(self):
        if not utils.is_valid_passport_no(self.data["passport_no"]):
            self.v.append("Invalid Passport number: passport_no")

    def _check_passport_origin(self):
        if not utils.is_valid_passport_origin(self.data["passport_origin"]):
            self.v.append("Invalid Passport origin: passport_origin")

    def _check_id_type(self):
        if self.data["id_type"] not in ["sa_id", "passport", "none"]:
            self.v.append("Invalid data: id_type not sa_id/passport/none")

    def _check_baby_dob(self):
        if not utils.is_valid_date(self.data["baby_dob"]):
            self.v.append("Invalid date: baby_dob")
        elif utils.get_baby_age(utils.get_today(), self.data["baby_dob"]) < 0:
            self.v.append("Invalid date: baby_dob is in the future")

    def _check_language(self):
        if not utils.is_valid_lang(self.data["language"]):
            self.v.append("Invalid Language: language")

    def _check_edd(self):
        if not utils.is_valid_date(self.data["edd"]):
            self.v.append("Invalid date: edd")

    def _check_faccode(self):
        if not utils.is_valid_faccode(self.data["faccode"]):
            self.v.append("Invalid Clinic Code: faccode")

    def _check_consent(self):
        if self.data["consent"] is not True:
            self.v.append("Invalid Consent: consent must be True")

    def _check_mha(self):
        if not utils.is_valid_mha(self.data["mha"]):
            self.v.append("Invalid Clinic Code: mha")

    def _check_swt(self):
        if not utils.is_valid_swt(self.data["swt"]):
            self.v.append("Invalid Clinic Code: swt")

    def _check_field_values(self, required_fields):
        _check_map = {
            "operator_id": self._check_operator_id,
            "msisdn_registrant": self._check_msisdn_registrant,
            "msisdn_device": self._check_msisdn_device,
            "sa_id_no": self._check_sa_id_no,
            "mom_dob": self._check_mom_dob,
            "passport_no": self._check_passport_no,
            "passport_origin": self._check_passport_origin,
            "id_type": self._check_id_type,
            "baby_dob": self._check_baby_dob,
            "language": self._check_language,
            "edd": self._check_edd,
            "faccode": self._check_faccode,
            "consent": self._check_consent,
            "mha": self._check_mha,
            "swt": self._check_swt,
        }
        for field in sorted(self.data.keys()):
            if field in required_fields or self.data.get(field) is not None:
                _check_map[field]()

    def _check_for_unrecognised_fields(self):
        recognised_fields = [
            "operator_id", "msisdn_registrant", "msisdn_device", "sa_id_no",
            "mom_dob", "passport_no", "passport_origin", "id_type", "baby_dob",
            "language", "edd", "faccode", "consent", "mha", "swt"
        ]
        for field in list(self.data.keys()):
            if field not in recognised_fields:
                self.v.append("Unrecognised field: %s" % field)

    def _get_required_id_type_fields(self):
        id_type = self.data.get("id_type")
        if id_type == "sa_id":
            return ["sa_id_no", "mom_dob"]
        elif id_type == "passport":
            return ["passport_no", "passport_origin"]
        elif id_type == "none":
            return ["mom_dob"]
        else:
            return []

    def _get_required_fields(self):
        # Determine which fields are required
        required_fields = []
        # . clinic
        if self.reg_type == "momconnect_prebirth" and \
           self.source.authority == "hw_full":
            required_fields = [
                "operator_id", "msisdn_registrant", "msisdn_device",
                "language", "edd", "faccode", "consent", "id_type"]
            required_fields += self._get_required_id_type_fields()
        # . chw
        elif self.reg_type == "momconnect_prebirth" and \
                self.source.authority == "hw_partial":
            required_fields = [
                "operator_id", "msisdn_registrant", "msisdn_device",
                "language", "consent", "id_type"]
            required_fields += self._get_required_id_type_fields()
        # . public
        elif self.reg_type == "momconnect_prebirth" and \
                self.source.authority == "patient":
            required_fields = [
                "operator_id", "msisdn_registrant", "msisdn_device",
                "language", "consent"]
        # . postbirth registrations are not allowed yet
        # ...
        # . nurseconnect
        elif self.reg_type == "nurseconnect":
            required_fields = [
                "operator_id", "msisdn_registrant", "msisdn_device",
                "language", "faccode"]
        # # . pmtct_prebirth
        elif self.reg_type == "pmtct_prebirth":
            required_fields = [
                "operator_id", "mom_dob", "edd", "language"]
        elif self.reg_type == "pmtct_postbirth":
            required_fields = [
                "operator_id", "mom_dob", "baby_dob", "language"]
        # . loss direct registrations are not allowed yet
        # ...
        return required_fields

    def _check_required_fields_present(self, required_fields):
        # Determine if required fields are available
        if len(required_fields) == 0:
            self.v.append("Error. reg_type: %s. authority: %s" % (
                self.reg_type, self.source.authority))
        else:
            for field in sorted(required_fields):
                if field not in self.data.keys():
                    self.v.append("Missing field: %s" % field)
                elif self.data.get(field) is None:
                    self.v.append(
                        "Required field should not be None: %s" % field)

    def clean(self, *args, **kwargs):
        super(Registration, self).clean(*args, **kwargs)
        self.v = []

        # Validate the registrant_id
        self._check_registrant_id()
        # Validate the reg_type
        self._check_reg_type()

        # Validate the `data` JSONField
        # . Check for data fields that we don't recognise
        self._check_for_unrecognised_fields()
        # . Check that the required fields are present
        required_fields = self._get_required_fields()
        self._check_required_fields_present(required_fields)
        # . Check the data field values only if there are no errors yet
        if len(self.v) == 0:
            self._check_field_values(required_fields)

        # Raise the validation errors encountered if any
        if len(self.v) > 0:
            raise ValidationError(self.v)
        else:
            self.validated = True

    def save(self, *args, **kwargs):
        self.full_clean()
        super(Registration, self).save(*args, **kwargs)


@python_2_unicode_compatible
class SubscriptionRequest(models.Model):
    """ A data model that maps to the Stagebased Store
    Subscription model. Created after a successful Registration
    validation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.CharField(max_length=36, null=False, blank=False)
    messageset = models.IntegerField(null=False, blank=False)
    next_sequence_number = models.IntegerField(default=1, null=False,
                                               blank=False)
    lang = models.CharField(max_length=6, null=False, blank=False)
    schedule = models.IntegerField(default=1)
    metadata = JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def serialize_hook(self, hook):
        # optional, there are serialization defaults
        # we recommend always sending the Hook
        # metadata along for the ride as well
        return {
            'hook': hook.dict(),
            'data': {
                'id': str(self.id),
                'identity': self.identity,
                'messageset': self.messageset,
                'next_sequence_number': self.next_sequence_number,
                'lang': self.lang,
                'schedule': self.schedule,
                'metadata': self.metadata,
                'created_at': self.created_at.isoformat(),
                'updated_at': self.updated_at.isoformat()
            }
        }

    def __str__(self):
        return str(self.id)
