# Generated by Django 2.2.20 on 2022-04-13 06:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("ada", "0013_remove_redirecturl_url")]

    operations = [
        migrations.CreateModel(
            name="AdaAssessment",
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
                ("contact_id", models.UUIDField()),
                ("step", models.IntegerField(null=True)),
                ("optionId", models.IntegerField(blank=True, null=True)),
                ("user_input", models.TextField(blank=True, null=True)),
                ("title", models.TextField(blank=True, null=True)),
                ("description", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        )
    ]
