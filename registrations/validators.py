from datetime import datetime

from iso6709 import Location
from rest_framework.serializers import ValidationError

from ndoh_hub import utils


def edd(value):
    if not utils.is_valid_edd_date(value):
        raise ValidationError("Must be in the future, but less than 43 weeks away")


def baby_dob(value):
    if not utils.is_valid_baby_dob_date(value):
        raise ValidationError("Must be in the past, but less than 2 years old")


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


def posix_timestamp(value):
    try:
        datetime.fromtimestamp(int(value))
    except ValueError:
        raise ValidationError("Invalid POSIX timestamp.")


def geographic_coordinate(value):
    try:
        Location(value)
    except AttributeError:
        raise ValidationError("Invalid ISO6709 geographic coordinate")
