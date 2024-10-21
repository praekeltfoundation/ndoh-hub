import csv
import json

from ndoh_hub.constants import WHATSAPP_LANGUAGE_MAP


class BaseMigration:
    TEMPLATE_NAME = ""

    def get_template_variables(self, message):
        raise NotImplementedError()

    def get_template_name(self, message):
        if self.TEMPLATE_NAME == "":
            raise NotImplementedError()
        return self.TEMPLATE_NAME

    def run(self, input, output):
        reader = csv.DictReader(input)
        writer = csv.DictWriter(output, reader.fieldnames)
        writer.writeheader()
        for row in reader:
            metadata = json.loads(row["metadata"])
            metadata["template"] = {
                "name": self.get_template_name(row),
                "language": WHATSAPP_LANGUAGE_MAP[row["lang"]],
                "variables": self.get_template_variables(row),
            }
            row["metadata"] = json.dumps(metadata)
            writer.writerow(row)
