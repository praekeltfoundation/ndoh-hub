from django.core.management import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):

    help = ("Submit registrations to Jembi. This command is useful if for "
            "some reason registrations weren't submitted or failed to submit "
            "and need to be submitted again")

    def add_arguments(self, parser):
        parser.add_argument(
            '--since', type=parse_datetime,
            help='Filter for created_at since (required YYYY-MM-DD HH:MM:SS)')
        parser.add_argument(
            '--until', type=parse_datetime,
            help='Filter for created_at until (required YYYY-MM-DD HH:MM:SS)')

    def handle(self, *args, **options):
        from registrations.models import Registration
        from registrations.tasks import push_registration_to_jembi
        since = options['since']
        until = options['until']

        if not since:
            raise CommandError('--since is a required parameter')

        if not until:
            raise CommandError('--until is a required parameter')

        registrations = Registration.objects.filter(
            created_at__gte=since,
            created_at__lte=until,
            validated=True)
        self.stdout.write(
            'Submitting %s registrations.' % (registrations.count(),))
        for registration in registrations:
            push_registration_to_jembi.apply_async(kwargs={
                'registration_id': str(registration.pk),
            })
            self.stdout.write(str(registration.pk))
        self.stdout.write('Done.')
