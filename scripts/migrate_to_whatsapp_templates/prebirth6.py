import sys

from .base import BaseMigration


class Prebirth6Migration(BaseMigration):
    TEMPLATE_NAME = "mc_prebirth"

    def sequence_number_to_weeks(self, sequence_number):
        MSGS_PER_WEEK = 7
        STARTING_WEEK = 38
        return ((sequence_number + 6) // MSGS_PER_WEEK) + STARTING_WEEK

    def get_template_variables(self, message):
        return [
            str(self.sequence_number_to_weeks(int(message["sequence_number"]))),
            message["text_content"],
        ]


if __name__ == "__main__":
    Prebirth6Migration().run(sys.stdin, sys.stdout)
