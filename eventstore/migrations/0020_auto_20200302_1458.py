# Generated by Django 2.2.4 on 2020-03-02 14:58

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("eventstore", "0019_babydobswitch_eddswitch")]

    operations = [
        migrations.CreateModel(
            name="DeliveryFailure",
            fields=[
                (
                    "contact_id",
                    models.CharField(max_length=255, primary_key=True, serialize=False),
                ),
                ("number_of_failures", models.IntegerField(default=0)),
            ],
        ),
        migrations.AlterField(
            model_name="event",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("sent", "sent"),
                    ("delivered", "delivered"),
                    ("read", "read"),
                    ("failed", "failed"),
                ],
                max_length=255,
            ),
        ),
    ]
