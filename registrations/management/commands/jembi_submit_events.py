from django.core.management import BaseCommand
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from eventstore.tasks import push_to_jembi_api


class Command(BaseCommand):

    help = (
        "Submit events to Jembi. This command is useful if for some reason events "
        "weren't submitted or failed to submit, or if the submission was switched off "
        "due to issues or outages downstream."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=parse_datetime,
            default=None,
            help="Filter for timestamp since (YYYY-MM-DD HH:MM:SS)",
        )
        parser.add_argument(
            "--until",
            type=parse_datetime,
            default=None,
            help="Filter for timestamp until (YYYY-MM-DD HH:MM:SS)",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Submit all events, not only ones that haven't been submitted",
        )
        parser.add_argument(
            "--submit",
            action="store_true",
            help="Actually submits the events to Jembi, instead of doing a dry run",
        )

    def handle(self, *args, **options):
        from registrations.models import JembiSubmission

        if options["all"]:
            events = JembiSubmission.objects.all()
        else:
            events = JembiSubmission.objects.filter(submitted=False)

        if options["since"]:
            events = events.filter(timestamp__gte=timezone.make_aware(options["since"]))
        if options["until"]:
            events = events.filter(timestamp__lte=timezone.make_aware(options["until"]))

        self.stdout.write(f"Submitting {events.count()} events.")

        if not options["submit"]:
            self.stdout.write("WARNING: --submit not specified, not submitting events")
            return

        for event in events.values_list("pk", "path", "request_data").iterator():
            push_to_jembi_api.delay(event)
