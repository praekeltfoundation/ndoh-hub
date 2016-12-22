import csv

from django.core.management.base import BaseCommand
from django.db import connection
from six.moves import zip


class Command(BaseCommand):
    help = 'Generate reports for PMTCT registrations.'

    def query(self, query_string):
        cursor = connection.cursor()
        cursor.execute(query_string)
        col_names = [desc[0] for desc in cursor.description]
        while True:
            row = cursor.fetchone()
            if row is None:
                break

            row_dict = dict(zip(col_names, row))
            yield row_dict

        return

    def query_to_csv(self, fp, column_names, query):
        records = self.query(query)
        writer = csv.DictWriter(self.stdout, column_names)
        writer.writeheader()
        for record in records:
            writer.writerow(record)

    def handle(self, *args, **kwargs):
        query = """
        SELECT
         reg_type AS "Registration Type",
         to_char(created_at, 'YYYY-MM-DD') AS created,
         count(*) AS count
        FROM
         registrations_registration
        WHERE
         reg_type LIKE 'pmtct%'
        AND
         validated = true
        GROUP BY
         reg_type,
         created
        """
        self.query_to_csv(
            self.stdout,
            ['Registration Type', 'created', 'count'],
            query)
