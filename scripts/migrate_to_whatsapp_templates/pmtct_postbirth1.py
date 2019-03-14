import sys

from .base import BaseMigration


class PMTCTPostbirth1Migration(BaseMigration):
    TEMPLATE_NAME = "mc_postbirth1"

    def sequence_number_to_weeks(self, sequence_number):
        MSGS_PER_WEEK = 2
        return ((sequence_number - 1) // MSGS_PER_WEEK)

    def get_template_variables(self, message):
        return [
            str(self.sequence_number_to_weeks(int(message["sequence_number"]))),
            message["text_content"],
        ]


if __name__ == "__main__":
    PMTCTPostbirth1Migration().run(sys.stdin, sys.stdout)
