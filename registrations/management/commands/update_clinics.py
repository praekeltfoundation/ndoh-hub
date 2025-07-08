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
        if row["longitude"] and row["latitude"]:
            lng = float(row["longitude"])
            lat = float(row["latitude"])
            return self.format_location(lat, lng)

    def handle(self, *args, **options):
        for csv_file in options["csv_file"]:
            reader = csv.DictReader(open(csv_file))

            for row in reader:
                clinic = ClinicCode.objects.filter(uid=row["OU5uid"]).first()
                if clinic:
                    clinic.area_type = row["OrgUnitRuralUrban"]
                    clinic.unit_type = row["OrgUnitType"]
                    clinic.district = row["OU3short"]
                    clinic.municipality = row["OU4short"]
                    clinic.save()
                    print(f"Updated: {clinic.value}")
