import sys

from scripts.migrate_to_whatsapp_templates.base import BaseMigration


class PMTCTPrebirth3Migration(BaseMigration):
    TEMPLATE_NAME = "mc_prebirth"

    def sequence_number_to_weeks(self, sequence_number):
        MSGS_PER_WEEK = 3
        STARTING_WEEK = 36
        return ((sequence_number - 1) // MSGS_PER_WEEK) + STARTING_WEEK

    def get_template_variables(self, message):
        return [
            str(self.sequence_number_to_weeks(int(message["sequence_number"]))),
            message["text_content"],
        ]


if __name__ == "__main__":
    PMTCTPrebirth3Migration().run(sys.stdin, sys.stdout)
