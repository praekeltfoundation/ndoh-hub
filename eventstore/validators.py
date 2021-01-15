from django.core.exceptions import ValidationError


def validate_true(value):
    if value is not True:
        raise ValidationError(f"{value} is not true")
