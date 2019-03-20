import sys

from .base import BaseMigration


class Postbirth1Migration(BaseMigration):
    MSGS_PER_WEEK = 2

    def get_template_name(self, message):
        if int(message["sequence_number"]) < 17:
            return "mc_postbirth1"
        return "mc_postbirth2"

    def get_weeks_from_sequence_number(self, sequence_number):
        return (sequence_number - 1) // self.MSGS_PER_WEEK

    def get_months_from_sequence_number(self, sequence_number):
        WEEKS_PER_MONTH = 52 / 12
        return int((sequence_number - 1) / (self.MSGS_PER_WEEK * WEEKS_PER_MONTH))

    def get_template_variables(self, message):
        sequence_number = int(message["sequence_number"])
        content = message["text_content"]
        if sequence_number < 17:
            return [str(self.get_weeks_from_sequence_number(sequence_number)), content]
        return [str(self.get_months_from_sequence_number(sequence_number)), content]


if __name__ == "__main__":
    Postbirth1Migration().run(sys.stdin, sys.stdout)
