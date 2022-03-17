# Generated by Django 2.2.24 on 2022-03-17 11:40

import functools

from django.db import migrations, models

import eventstore.validators


class Migration(migrations.Migration):

    dependencies = [
        ("mqr", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BaselineSurveyResult",
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
                (
                    "msisdn",
                    models.CharField(
                        max_length=255,
                        validators=[
                            functools.partial(
                                eventstore.validators._phone_number,
                                *(),
                                **{"country": "ZA"}
                            )
                        ],
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "breastfeed",
                    models.CharField(
                        choices=[("yes", "Yes"), ("no", "No"), ("skip", "Skip")],
                        default=None,
                        max_length=4,
                        null=True,
                    ),
                ),
                (
                    "breastfeed_period",
                    models.CharField(
                        choices=[
                            ("0_3_months", "0-3 months"),
                            ("4_5_months", "4-5 months"),
                            ("6_months", "For 6 months"),
                            ("over_6_months", "Longer than 6 months"),
                            ("not_only_breastfeed", "I don't want to only breastfeed"),
                            ("dont_know", "I don't know"),
                            ("skip", "Skip"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "vaccine_importance",
                    models.CharField(
                        choices=[
                            ("strongly_agree", "I strongly agree"),
                            ("agree", "I agree"),
                            ("neutral", "I don't agree or disagree"),
                            ("disagree", "I disagree"),
                            ("strongly_disagree", "I strongly disagree"),
                            ("skip", "Skip"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "vaccine_benifits",
                    models.CharField(
                        choices=[
                            ("strongly_agree", "I strongly agree"),
                            ("agree", "I agree"),
                            ("neutral", "I don't agree or disagree"),
                            ("disagree", "I disagree"),
                            ("strongly_disagree", "I strongly disagree"),
                            ("skip", "Skip"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "clinic_visit_frequency",
                    models.CharField(
                        choices=[
                            ("more_than_once_a_month", "More than once a month"),
                            ("once_a_month", "Once a month"),
                            ("once_2_3_months", "Once every  2 to 3 months"),
                            ("once_4_5_months", "Once every  4 to 5 months"),
                            ("once_6_9_months", "Once every 6 to 9 months"),
                            ("never", "Never"),
                            ("skip", "Skip"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "vegetables",
                    models.CharField(
                        choices=[("yes", "Yes"), ("no", "No"), ("skip", "Skip")],
                        default=None,
                        max_length=4,
                        null=True,
                    ),
                ),
                (
                    "fruit",
                    models.CharField(
                        choices=[("yes", "Yes"), ("no", "No"), ("skip", "Skip")],
                        default=None,
                        max_length=4,
                        null=True,
                    ),
                ),
                (
                    "dairy",
                    models.CharField(
                        choices=[("yes", "Yes"), ("no", "No"), ("skip", "Skip")],
                        default=None,
                        max_length=4,
                        null=True,
                    ),
                ),
                (
                    "liver_frequency",
                    models.CharField(
                        choices=[
                            ("2_3_times_week", "2-3 times a week"),
                            ("once_a_week", "Once a week"),
                            ("once_a_month", "Once a month"),
                            ("less_once_a_month", "Less than once a month"),
                            ("never", "Never"),
                            ("skip", "Skip"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "danger_sign",
                    models.CharField(
                        choices=[
                            (
                                "swollen_feet_legs",
                                "Swollen feet and legs even after sleep",
                            ),
                            ("bloating", "Bloating"),
                            ("gas", "Gas"),
                            ("skip", "Skip"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "marital_status",
                    models.CharField(
                        choices=[
                            ("never_married", "Never married"),
                            ("married", "Married"),
                            ("separated_or_divorced", "Separated or divorced"),
                            ("widowed", "Widowed"),
                            ("parter_or_boyfriend", "Have a partner or boyfriend"),
                            ("skip", "Skip"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
                (
                    "education_level",
                    models.CharField(
                        choices=[
                            ("less_grade_7", "Less than Grade 7"),
                            ("between_grade_7_12", "Between Grades 7-12"),
                            ("matric", "Matric"),
                            ("diploma", "Diploma"),
                            ("degree_or_higher", "University degree or higher"),
                            ("skip", "Skip"),
                        ],
                        default=None,
                        max_length=20,
                        null=True,
                    ),
                ),
            ],
        ),
    ]
