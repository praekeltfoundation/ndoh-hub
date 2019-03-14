import sys

from .base import BaseMigration


class PMTCTPostbirth2Migration(BaseMigration):
    MSGS_PER_WEEK = 1
    WEEKS_OFFSET = 2

    def get_template_name(self, message):
        if int(message["sequence_number"]) < 7:
            return "mc_postbirth1"
        return "mc_postbirth2"

    def get_weeks_from_sequence_number(self, sequence_number):
        return (sequence_number - 1) // self.MSGS_PER_WEEK + self.WEEKS_OFFSET

    def get_months_from_sequence_number(self, sequence_number):
        WEEKS_PER_MONTH = 52 / 12
        return int(
            (sequence_number - 1 + self.WEEKS_OFFSET * self.MSGS_PER_WEEK)
            / (self.MSGS_PER_WEEK * WEEKS_PER_MONTH)
        )

    def get_template_variables(self, message):
        sequence_number = int(message["sequence_number"])
        content = message["text_content"]
        if sequence_number < 7:
            return [str(self.get_weeks_from_sequence_number(sequence_number)), content]
        return [str(self.get_months_from_sequence_number(sequence_number)), content]


if __name__ == "__main__":
    PMTCTPostbirth2Migration().run(sys.stdin, sys.stdout)
