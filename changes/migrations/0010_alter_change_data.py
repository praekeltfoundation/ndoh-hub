# Generated by Django 4.1 on 2023-03-24 13:18

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("changes", "0009_add_registrant_id_index_to_changes"),
    ]

    operations = [
        migrations.AlterField(
            model_name="change",
            name="data",
            field=models.JSONField(blank=True, null=True),
        ),
    ]