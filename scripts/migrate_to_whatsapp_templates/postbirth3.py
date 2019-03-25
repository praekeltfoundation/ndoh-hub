import sys

from scripts.migrate_to_whatsapp_templates.base import BaseMigration


class Postbirth3Migration(BaseMigration):
    TEMPLATE_NAME = "mc_postbirth3"

    def get_template_variables(self, message):
        return [message["text_content"]]


if __name__ == "__main__":
    Postbirth3Migration().run(sys.stdin, sys.stdout)
