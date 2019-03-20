import sys

from scripts.migrate_to_whatsapp_templates.base import BaseMigration


class ServiceInfo(BaseMigration):
    TEMPLATE_NAME = "mc_important_info"

    def get_template_variables(self, message):
        return [message["text_content"]]


if __name__ == "__main__":
    ServiceInfo().run(sys.stdin, sys.stdout)
