import csv
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.core.validators import URLValidator
from django.db.models import Q
from seed_services_client import HubApiClient, IdentityStoreApiClient

from registrations.models import Registration
from registrations.tasks import add_personally_identifiable_fields, get_risk_status

# NOTE: Python 3 compatibility
try:
    from urlparse import urlparse, parse_qs
except ImportError:
    from urllib.parse import urlparse, parse_qs


def mk_validator(django_validator):
    def validator(inputstr):
        django_validator()(inputstr)
        return inputstr

    return validator


def parse_cursor_params(cursor):
    parse_result = urlparse(cursor)
    params = parse_qs(parse_result.query)
    return dict([(key, value[0]) for key, value in params.items()])


class Command(BaseCommand):
    help = "Generate risks report for PMTCT registrations"

    def add_arguments(self, parser):
        parser.add_argument("--hub-url", type=mk_validator(URLValidator))
        parser.add_argument("--hub-token", type=str)
        parser.add_argument("--identity-store-url", type=mk_validator(URLValidator))
        parser.add_argument("--identity-store-token", type=str)
        parser.add_argument("--group", type=str, default="risk_status")
        parser.add_argument("--output", type=str)

    def handle(self, *options, **kwargs):
        self.identity_cache = {}

        hub_token = kwargs["hub_token"]
        hub_url = kwargs["hub_url"]
        id_store_token = kwargs["identity_store_token"]
        id_store_url = kwargs["identity_store_url"]
        group = kwargs["group"]

        headers = ["risk", "count"]
        if group == "msisdn":
            if not id_store_token or not id_store_url:
                raise CommandError(
                    "Please make sure the --identity-store-url and "
                    "--identity-store-token is set."
                )

            ids_client = IdentityStoreApiClient(id_store_token, id_store_url)
            headers = ["msisdn", "risk"]

        output = self.stdout
        if kwargs["output"]:
            output = open(kwargs["output"], "w")

        results = defaultdict(int)

        def add_to_result(risk, reg):
            if group == "msisdn":
                identity = self.get_identity(ids_client, reg)

                if identity:
                    details = identity.get("details", {})
                    default_addr_type = details.get("default_addr_type")
                    if default_addr_type:
                        addresses = details.get("addresses", {})
                        msisdns = addresses.get(default_addr_type, {}).keys()
                    else:
                        msisdns = []

                    results[", ".join(msisdns)] = 1 if risk == "high" else 0
            else:
                results[risk] += 1

        if hub_token and hub_url:
            hub_client = HubApiClient(hub_token, hub_url)

            for source in (1, 3):
                registrations = hub_client.get_registrations(
                    {"source": source, "validated": True}
                )["results"]

                for registration in registrations:
                    mom_dob = registration["data"].get("mom_dob")
                    if not mom_dob:
                        identity = self.get_identity(
                            ids_client, registration["registrant_id"]
                        )
                        if not identity:
                            continue
                        mom_dob = identity["details"].get("mom_dob")

                    risk = get_risk_status(
                        registration["reg_type"],
                        mom_dob,
                        registration["data"].get("edd"),
                    )

                    add_to_result(risk, registration["registrant_id"])

        else:
            registrations = Registration.objects.filter(
                Q(reg_type="pmtct_postbirth")
                | Q(reg_type="pmtct_prebirth")
                | Q(reg_type="whatsapp_pmtct_postbirth")
                | Q(reg_type="whatsapp_pmtct_prebirth"),
                validated=True,
            )

            for registration in registrations.iterator():
                add_personally_identifiable_fields(registration)
                risk = get_risk_status(
                    registration.reg_type,
                    registration.data["mom_dob"],
                    registration.data.get("edd"),
                )

                add_to_result(risk, registration.registrant_id)

        writer = csv.DictWriter(output, headers)
        writer.writeheader()
        for risk, count in results.items():
            writer.writerow({headers[0]: risk, headers[1]: count})

    def get_identity(self, ids_client, identity):
        if identity in self.identity_cache:
            return self.identity_cache[identity]

        identity_object = ids_client.get_identity(identity)
        self.identity_cache[identity] = identity_object
        return identity_object
