import sys

from .base import BaseMigration


class LossMigration(BaseMigration):
    TEMPLATE_NAME = "mc_loss"

    def get_template_variables(self, message):
        return [message["text_content"]]


if __name__ == "__main__":
    LossMigration().run(sys.stdin, sys.stdout)
