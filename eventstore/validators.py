import re
from datetime import date

from django.core.exceptions import ValidationError

from registrations.models import ClinicCode


def validate_true(value):
    if value is not True:
        raise ValidationError(f"{value} is not true")


def luhn_verify(value):
    digits = list(map(int, value))
    odd_sum = sum(digits[-1::-2])
    even_sum = sum([sum(divmod(2 * d, 10)) for d in digits[-2::-2]])
    return (odd_sum + even_sum) % 10 == 0


def validate_sa_id_number(value):
    match = re.match(
        r"^"
        r"(?P<year>\d{2})"
        r"(?P<month>\d{2})"
        r"(?P<day>\d{2})"
        r"(?P<gender>\d{4})"
        r"(?P<citizen>0|1)"
        r"(8|9)"
        r"(?P<checksum>\d{1})$",
        value,
    )
    if not match:
        raise ValidationError("Invalid ID number format")
    year = date.today().year % 100 + int(match.group("year"))
    if year > date.today().year:
        year -= 100
    try:
        date(year, int(match.group("month")), int(match.group("day")))
    except ValueError as e:
        raise ValidationError(f"Invalid ID number date: {str(e)}")
    if int(match.group("gender")) >= 5000:
        raise ValidationError("Invalid ID number: for male")
    if not luhn_verify(value):
        raise ValidationError("Invalid ID number: Failed Luhn checksum")


def validate_facility_code(value):
    if not ClinicCode.objects.filter(value=value).exists():
        raise ValidationError("Invalid Facility Code")
