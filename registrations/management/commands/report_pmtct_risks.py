import csv
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db.models import Q

from registrations.models import Registration
from registrations.tasks import get_risk_status


class Command(BaseCommand):
    help = 'Generate risks report for PMTCT registrations'

    def handle(self, *options, **kwargs):
        registrations = Registration.objects.filter(
            Q(reg_type='pmtct_postbirth') | Q(reg_type='pmtct_prebirth'))
        results = defaultdict(int)
        for registration in registrations:
            risk = get_risk_status(registration.reg_type,
                                   registration.data["mom_dob"],
                                   registration.data["edd"])
            results[risk] += 1

        writer = csv.DictWriter(self.stdout, ['risk', 'count'])
        writer.writeheader()
        for risk, count in results.items():
            writer.writerow({'risk': risk, 'count': count})
