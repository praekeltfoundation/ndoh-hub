import sys

from scripts.migrate_to_whatsapp_templates.base import BaseMigration


class PublicMigration(BaseMigration):
    TEMPLATE_NAME = "mc_message"

    def get_template_variables(self, message):
        return [message["text_content"]]


if __name__ == "__main__":
    PublicMigration().run(sys.stdin, sys.stdout)
