# Generated by Django 2.2.13 on 2021-01-18 09:50

from django.db import migrations, models

import eventstore.validators


class Migration(migrations.Migration):

    dependencies = [
        (
            "eventstore",
            "0038_importerror_importrow_momconnectimport_squashed_0040_small_integer_fields",
        )
    ]

    operations = [
        migrations.AlterField(
            model_name="importerror",
            name="error_type",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "File is not a CSV"),
                    (1, "Fields {} not found in header"),
                    (2, "Field {} failed validation: {}"),
                    (3, "Failed validation: {}"),
                    (4, "Mother is opted out and has not chosen to opt in again"),
                    (5, "Mother is already receiving prebirth messages"),
                ]
            ),
        ),
        migrations.AlterField(
            model_name="importrow",
            name="facility_code",
            field=models.CharField(
                max_length=6, validators=[eventstore.validators.validate_facility_code]
            ),
        ),
    ]