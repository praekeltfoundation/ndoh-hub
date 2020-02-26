# Generated by Django 2.2.4 on 2020-02-25 07:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("eventstore", "0019_babydobswitch_eddswitch")]

    operations = [
        migrations.CreateModel(
            name="DeliveryFailure",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("contact_id", models.CharField(blank=True, max_length=255)),
                ("number_of_failures", models.IntegerField(default=0)),
            ],
        )
    ]
