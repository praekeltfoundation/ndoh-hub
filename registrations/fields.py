import phonenumbers
from rest_framework import serializers


class PhoneNumberField(serializers.Field):
    """
    Phone Numbers are serialized into E164 international format
    """

    default_error_messages = {
        "cannot_parse": "Cannot parse: {error}",
        "not_possible": "Not a possible phone number",
        "not_valid": "Not a valid phone number",
    }

    def __init__(self, *args, country_code=None, **kwargs):
        self.country_code = country_code
        return super().__init__(*args, **kwargs)

    def to_representation(self, obj):
        return phonenumbers.format_number(obj, phonenumbers.PhoneNumberFormat.E164)

    def to_internal_value(self, data):
        try:
            p = phonenumbers.parse(data, self.country_code)
        except phonenumbers.phonenumberutil.NumberParseException as e:
            self.fail("cannot_parse", error=str(e))
        if not phonenumbers.is_possible_number(p):
            self.fail("not_possible")
        if not phonenumbers.is_valid_number(p):
            self.fail("not_valid")
        p.raw_input = data
        return p
