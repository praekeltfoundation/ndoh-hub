from uuid import UUID

from celery import chain
from django.core.management import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from registrations.tasks import (
    add_personally_identifiable_fields,
    remove_personally_identifiable_fields,
)


class Command(BaseCommand):

    help = (
        "Submit registrations to Jembi. This command is useful if for "
        "some reason registrations weren't submitted or failed to submit "
        "and need to be submitted again"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            type=parse_datetime,
            help="Filter for created_at since (required YYYY-MM-DD HH:MM:SS)",
        )
        parser.add_argument(
            "--until",
            type=parse_datetime,
            help="Filter for created_at until (required YYYY-MM-DD HH:MM:SS)",
        )
        parser.add_argument(
            "--source",
            type=int,
            default=None,
            help="The source to limit registrations to.",
        )
        parser.add_argument(
            "--registration",
            type=UUID,
            nargs="+",
            default=None,
            help=(
                "UUIDs for registrations to fire manually. Use if finer "
                "controls are needed than `since` and `until` date ranges."
            ),
        )

    def handle(self, *args, **options):
        from registrations.models import Registration
        from registrations.tasks import BasePushRegistrationToJembi

        since = options["since"]
        until = options["until"]
        source = options["source"]
        registration_uuids = options["registration"]

        if not (all([since, until]) or registration_uuids):
            raise CommandError(
                "At a minimum please specify --since and --until "
                "or use --registration to specify one or more registrations"
            )

        registrations = Registration.objects.all()

        if since and until:
            since = timezone.make_aware(since)
            until = timezone.make_aware(until)
            registrations = registrations.filter(
                created_at__gte=since, created_at__lte=until, validated=True
            )

        if source is not None:
            registrations = registrations.filter(source__pk=source)

        if registration_uuids:
            registrations = registrations.filter(pk__in=registration_uuids)

        self.stdout.write("Submitting %s registrations." % (registrations.count(),))
        for registration in registrations:
            add_personally_identifiable_fields(registration)
            registration.save()
            jembi_task = BasePushRegistrationToJembi.get_jembi_task_for_registration(
                registration
            )
            task = chain(
                jembi_task.si(str(registration.pk)),
                remove_personally_identifiable_fields.si(str(registration.pk)),
            )
            task.delay()
            self.stdout.write(str(registration.pk))
        self.stdout.write("Done.")
