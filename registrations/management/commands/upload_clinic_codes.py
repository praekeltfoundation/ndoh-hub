from csv import DictReader

from django.core.management.base import BaseCommand

from registrations.models import ClinicCode


class Command(BaseCommand):
    help = (
        "This command takes in a CSV with the columns: uid, code, facility, province,"
        "and location, and creates/updates the cliniccodes in the database."
        "This will only add or update, it will not remove"
    )

    def add_arguments(self, parser):
        parser.add_argument("data_csv", type=str, help=("The CSV with the data in it"))

    def normalise_location(self, location):
        """
        Normalises the location from `[longitude,latitude]` to ISO6709
        """

        def fractional_part(f):
            if not float(f) % 1:
                return ""
            parts = f.split(".")
            return f".{parts[1]}"

        try:
            longitude, latitude = location.strip("[]").split(",")
            return (
                f"{int(float(latitude)):+03d}{fractional_part(latitude)}"
                f"{int(float(longitude)):+04d}{fractional_part(longitude)}"
                "/"
            )
        except (AttributeError, ValueError, TypeError):
            return None

    def handle(self, *args, **kwargs):
        updated = 0
        created = 0
        with open(kwargs["data_csv"]) as f:
            reader = DictReader(f)
            for row in reader:
                _, new = ClinicCode.objects.update_or_create(
                    uid=row["uid"].strip(),
                    defaults={
                        "code": row["code"].strip(),
                        "value": row["code"].strip(),
                        "name": row["facility"].strip(),
                        "province": {
                            "ec": "ZA-EC",
                            "fs": "ZA-FS",
                            "gp": "ZA-GT",
                            "kz": "ZA-NL",
                            "lp": "ZA-LP",
                            "mp": "ZA-MP",
                            "nc": "ZA-NC",
                            "nw": "ZA-NW",
                            "wc": "ZA-WC",
                        }[row["province"].strip()[:2].lower()],
                        "location": self.normalise_location(row["location"].strip()),
                    },
                )
                if new:
                    created += 1
                else:
                    updated += 1

        self.success(f"Updated {updated} and created {created} clinic codes")

    def log(self, level, msg):
        self.stdout.write(level(msg))

    def success(self, msg):
        self.log(self.style.SUCCESS, msg)
