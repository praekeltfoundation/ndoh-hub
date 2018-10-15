from rest_framework.serializers import ValidationError

from ndoh_hub import utils


def edd(value):
    if not utils.is_valid_edd_date(value):
        raise ValidationError("Must be in the future, but less than 43 weeks away")


def consent(value):
    if value is False:
        raise ValidationError("Mother must consent for registration")


def sa_id_no(value):
    if not utils.is_valid_sa_id_no(value):
        raise ValidationError("Invalid SA ID number. Must be 13 digits")


def passport_no(value):
    if not utils.is_valid_passport_no(value):
        raise ValidationError(
            "Invalid passport number. Must be at least 1 character long"
        )
