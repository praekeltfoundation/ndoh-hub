# Generated by Django 2.2.20 on 2021-05-11 06:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("ada", "0008_redirecturl_url")]

    operations = [
        migrations.AddField(
            model_name="redirecturlsentry",
            name="parameter",
            field=models.IntegerField(null=True),
        )
    ]