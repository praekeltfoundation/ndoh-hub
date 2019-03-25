import sys

from scripts.migrate_to_whatsapp_templates.base import BaseMigration


class Postbirth2Migration(BaseMigration):
    TEMPLATE_NAME = "mc_postbirth2"
    MSGS_PER_WEEK = 1
    WEEKS_OFFSET = 15

    def get_months_from_sequence_number(self, sequence_number):
        WEEKS_PER_MONTH = 52 / 12
        return int(
            (sequence_number - 1 + self.WEEKS_OFFSET * self.MSGS_PER_WEEK)
            / (self.MSGS_PER_WEEK * WEEKS_PER_MONTH)
        )

    def get_template_variables(self, message):
        sequence_number = int(message["sequence_number"])
        content = message["text_content"]
        return [str(self.get_months_from_sequence_number(sequence_number)), content]


if __name__ == "__main__":
    Postbirth2Migration().run(sys.stdin, sys.stdout)
