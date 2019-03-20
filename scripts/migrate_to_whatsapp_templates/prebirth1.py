import sys

from .base import BaseMigration


class Prebirth1Migration(BaseMigration):
    TEMPLATE_NAME = "mc_prebirth"

    def sequence_number_to_weeks(self, sequence_number):
        MSGS_PER_WEEK = 2
        STARTING_WEEK = 4
        return ((sequence_number + 1) // MSGS_PER_WEEK) + STARTING_WEEK

    def get_template_variables(self, message):
        return [
            str(self.sequence_number_to_weeks(int(message["sequence_number"]))),
            message["text_content"],
        ]


if __name__ == "__main__":
    Prebirth1Migration().run(sys.stdin, sys.stdout)
