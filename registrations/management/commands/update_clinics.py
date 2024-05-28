import ast
import csv

import pycountry
from django.core.management.base import BaseCommand

from registrations.models import ClinicCode


def clean_name(name):
    return name.lower().replace(" ", "").replace("-", "").split("(")[0]


PROVINCES = {
    clean_name(p.name): p.code for p in pycountry.subdivisions.get(country_code="ZA")
}


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument("csv_file", nargs="+", type=str)

    def format_location(self, latitude, longitude):
        """
        Returns the location in ISO6709 format
        """

        def fractional_part(f):
            if not f % 1:
                return ""
            parts = str(f).split(".")
            return f".{parts[1]}"

        # latitude integer part must be fixed width 2, longitude 3
        return (
            f"{int(latitude):+03d}"
            f"{fractional_part(latitude)}"
            f"{int(longitude):+04d}"
            f"{fractional_part(longitude)}"
            "/"
        )

    def get_province(self, row):
        return PROVINCES[clean_name(row["OU2short"])]

    def get_location(self, row):
        lng, lat = ast.literal_eval(row["coordinates"])
        return self.format_location(lat, lng)

    def handle(self, *args, **options):
        print(options["csv_file"])
        for csv_file in options["csv_file"]:
            reader = csv.DictReader(open(csv_file))

            for row in reader:
                clinic, created = ClinicCode.objects.update_or_create(
                    uid=row["OU5uid"],
                    defaults={
                        "code": row["OU5code"],
                        "value": row["OU5code"],
                        "name": row["organisationunitname"],
                        "province": self.get_province(row),
                        "location": self.get_location(row),
                        "area_type": row["OrgUnitRuralUrban"],
                        "unit_type": row["OrgUnitType"],
                        "district": row["OU3short"],
                        "municipality": row["OU4short"],
                    },
                )
                print(f"{'Created' if created else 'Updated'}: {clinic.value}")
