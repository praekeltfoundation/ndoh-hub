import uuid

from django.contrib.postgres.fields import JSONField
from django.contrib.auth.models import User
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

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
                                   null=True)
    updated_by = models.ForeignKey(User, related_name='registrations_updated',
                                   null=True)
    user = property(lambda self: self.created_by)

    def __str__(self):
        return str(self.id)

    def _check_registrant_id(self):
        if not utils.is_valid_uuid(self.registrant_id):
            self.v.append("Invalid UUID: registrant_id")

    def _check_operator_id(self):
        if "operator_id" not in self.data.keys():
            self.v.append("Missing field: operator_id")
        else:
            self.fields_to_check.remove("operator_id")
            if not utils.is_valid_uuid(self.data["operator_id"]):
                self.v.append("Invalid UUID: operator_id")

    def _check_msisdn_registrant(self):
        if "msisdn_registrant" not in self.data.keys():
            self.v.append("Missing field: msisdn_registrant")
        else:
            self.fields_to_check.remove("msisdn_registrant")
            if not utils.is_valid_msisdn(self.data["msisdn_registrant"]):
                self.v.append("Invalid MSISDN: msisdn_registrant")

    def _check_msisdn_device(self):
        if "msisdn_device" not in self.data.keys():
            self.v.append("Missing field: msisdn_device")
        else:
            self.fields_to_check.remove("msisdn_device")
            if not utils.is_valid_msisdn(self.data["msisdn_device"]):
                self.v.append("Invalid MSISDN: msisdn_device")

    def _check_sa_id_no(self):
        if "sa_id_no" not in self.data.keys():
            self.v.append("Missing field: sa_id_no")
        else:
            self.fields_to_check.remove("sa_id_no")
            if not utils.is_valid_sa_id_no(self.data["sa_id_no"]):
                self.v.append("Invalid SA ID number: sa_id_no")

    def _check_mom_dob(self):
        if "mom_dob" not in self.data.keys():
            self.v.append("Missing field: mom_dob")
        else:
            self.fields_to_check.remove("mom_dob")
            if not utils.is_valid_date(self.data["mom_dob"]):
                self.v.append("Invalid date: mom_dob")

    def _check_passport_no(self):
        if "passport_no" not in self.data.keys():
            self.v.append("Missing field: passport_no")
        else:
            self.fields_to_check.remove("passport_no")
            if not utils.is_valid_passport_no(self.data["passport_no"]):
                self.v.append("Invalid Passport number: passport_no")

    def _check_passport_origin(self):
        if "passport_origin" not in self.data.keys():
            self.v.append("Missing field: passport_origin")
        else:
            self.fields_to_check.remove("passport_origin")
            if not utils.is_valid_passport_origin(
              self.data["passport_origin"]):
                self.v.append("Invalid Passport origin: passport_origin")

    def _check_id(self):
        if "id_type" not in self.data.keys():
            self.v.append("Missing field: id_type")
        elif self.data["id_type"] not in ["sa_id", "passport", "none"]:
            self.v.append("Invalid data: id_type not sa_id/passport/none")
        else:
            self.fields_to_check.remove("id_type")
            if self.data["id_type"] == "sa_id":
                self._check_sa_id_no()
                self._check_mom_dob()
            elif self.data["id_type"] == "passport":
                self._check_passport_no()
                self._check_passport_origin()
            elif self.data["id_type"] == "none":
                self._check_mom_dob()

    def _check_baby_dob(self):
        if "baby_dob" not in self.data.keys():
            self.v.append("Missing field: baby_dob")
        else:
            self.fields_to_check.remove("baby_dob")
            if not utils.is_valid_date(self.data["baby_dob"]):
                self.v.append("Invalid date: baby_dob")
            elif utils.get_baby_age(utils.get_today(),
                                    self.data["baby_dob"]) < 0:
                self.v.append("Invalid date: baby_dob is in the future")

    def _check_language(self):
        if "language" not in self.data.keys():
            self.v.append("Missing field: language")
        else:
            self.fields_to_check.remove("language")
            if not utils.is_valid_lang(self.data["language"]):
                self.v.append("Invalid Language: language")

    def _check_edd(self):
        if "edd" not in self.data.keys():
            self.v.append("Missing field: edd")
        else:
            self.fields_to_check.remove("edd")
            if not utils.is_valid_date(self.data["edd"]):
                self.v.append("Invalid date: edd")

    def _check_faccode(self):
        if "faccode" not in self.data.keys():
            self.v.append("Missing field: faccode")
        else:
            self.fields_to_check.remove("faccode")
            if not utils.is_valid_faccode(self.data["faccode"]):
                self.v.append("Invalid Clinic Code: faccode")

    def _check_consent(self):
        if "consent" not in self.data.keys():
            self.v.append("Missing field: consent")
        else:
            self.fields_to_check.remove("consent")
            if self.data["consent"] is not True:
                self.v.append("Invalid Consent: consent must be True")

    def _check_superfluous_fields(self):
        if len(self.fields_to_check) > 0:
            self.v.append("Superfluous fields: %s" % ", ".join(
                self.fields_to_check))

    def validate_momconnect_clinic_prebirth(self):
        self._check_operator_id()
        self._check_msisdn_registrant()
        self._check_msisdn_device()
        self._check_id()  # contains additional checks
        self._check_language()
        self._check_edd()
        self._check_faccode()
        self._check_consent()

    def validate_momconnect_chw_prebirth(self):
        self._check_operator_id()
        self._check_msisdn_registrant()
        self._check_msisdn_device()
        self._check_id()  # contains additional checks
        self._check_language()
        self._check_consent()

    def validate_momconnect_public_prebirth(self):
        self._check_operator_id()
        self._check_msisdn_registrant()
        self._check_msisdn_device()
        self._check_language()
        self._check_consent()

    def validate_nurseconnect(self):
        self._check_operator_id()
        self._check_msisdn_registrant()
        self._check_msisdn_device()
        self._check_language()
        self._check_faccode()

    def validate_pmtct_prebirth(self):
        self._check_operator_id()
        self._check_mom_dob()
        self._check_edd()
        self._check_language()
        pass

    def validate_pmtct_postbirth(self):
        self._check_operator_id()
        self._check_mom_dob()
        self._check_baby_dob()
        self._check_language()

    def clean(self, *args, **kwargs):
        super(Registration, self).clean(*args, **kwargs)
        self.v = []

        # Validate the registrant_id
        self._check_registrant_id()

        # Validate the `data` JSONField
        self.fields_to_check = list(self.data.keys())
        # . MomConnect
        if self.reg_type == "momconnect_prebirth" and \
           self.source.authority == "hw_full":
            self.validate_momconnect_clinic_prebirth()
        elif self.reg_type == "momconnect_prebirth" and \
                self.source.authority == "hw_partial":
            self.validate_momconnect_chw_prebirth()
        elif self.reg_type == "momconnect_prebirth" and \
                self.source.authority == "patient":
            self.validate_momconnect_public_prebirth()
        # MomConnect postbirth registrations are not allowed yet
        # elif self.reg_type == "momconnect_postbirth" and \
        #         self.source.authority == "hw_full":
        #     self.validate_momconnect_clinic_postbirth()
        # . NurseConnect
        elif self.reg_type == "nurseconnect":
            self.validate_nurseconnect()
        # # . PMTCT
        elif self.reg_type == "pmtct_prebirth":
            self.validate_pmtct_prebirth()
        elif self.reg_type == "pmtct_postbirth":
            self.validate_pmtct_postbirth()
        # . Loss
        # Registrations are not allowed at the moment (you have to make a
        # pregnancy registration and then change to loss messaging), but there
        # have been mentions of its activation
        # elif self.reg_type == "loss_general":
        #     v = self._clean_loss_general()

        # If there are no validation errors at this point, check if extra
        # fields were submitted
        if len(self.v) == 0:
            self._check_superfluous_fields()

        if len(self.v) > 0:
            raise ValidationError(self.v)
        else:
            self.validated = True

    def save(self, *args, **kwargs):
        self.clean()
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
