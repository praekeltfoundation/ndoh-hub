# Generated by Django 2.2.24 on 2021-12-13 10:38

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('eventstore', '0050_askfeedback'),
    ]

    operations = [
        migrations.CreateModel(
            name='Feedback',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('contact_id', models.UUIDField()),
                ('functionality', models.CharField(choices=[('ask', 'Ask'), ('profile_update', 'Profile Update')], max_length=20)),
                ('positive', models.BooleanField(default=False)),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_by', models.CharField(blank=True, default='', max_length=255)),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, null=True)),
            ],
        ),
        migrations.DeleteModel(
            name='AskFeedback',
        ),
    ]
