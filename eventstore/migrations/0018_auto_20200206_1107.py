# Generated by Django 2.2.4 on 2020-02-06 11:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventstore', '0017_pmtctregistration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='optout',
            name='optout_type',
            field=models.CharField(choices=[('stop', 'Stop'), ('forget', 'Forget'), ('loss', 'Loss'), ('nonloss', 'Nonloss')], max_length=6),
        ),
    ]
