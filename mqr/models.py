from django.db import models

from eventstore.validators import za_phone_number


class MqrStrata(models.Model):
    province = models.CharField(max_length=25, null=False, blank=False)
    weeks_pregnant_bucket = models.CharField(max_length=12, null=False, blank=False)
    age_bucket = models.CharField(max_length=12, null=False, blank=False)
    next_index = models.IntegerField(default=0, null=False, blank=False)
    order = models.CharField(max_length=50, null=False, blank=False)


class BaselineSurveyResult(models.Model):
    class YesNoSkip:
        YES = "yes"
        NO = "no"
        SKIP = "skip"
        choices = ((YES, "Yes"), (NO, "No"), (SKIP, "Skip"))

    class BreastfeedPeriod:
        MONTHS_0_3 = "0_3_months"
        MONTHS_4_5 = "4_5_months"
        MONTHS_6 = "6_months"
        MONTHS_6_PLUS = "over_6_months"
        NOT_ONLY = "not_only_breastfeed"
        DONT_KNOW = "dont_know"
        SKIP = "skip"

        choices = (
            (MONTHS_0_3, "0-3 months"),
            (MONTHS_4_5, "4-5 months"),
            (MONTHS_6, "For 6 months"),
            (MONTHS_6_PLUS, "Longer than 6 months"),
            (NOT_ONLY, "I don't want to only breastfeed"),
            (DONT_KNOW, "I don't know"),
            (SKIP, "Skip"),
        )

    class AgreeDisagree:
        STRONG_AGREE = "strongly_agree"
        AGREE = "agree"
        NEUTRAL = "neutral"
        DISAGREE = "disagree"
        STRONG_DISAGREE = "strongly_disagree"
        SKIP = "skip"

        choices = (
            (STRONG_AGREE, "I strongly agree"),
            (AGREE, "I agree"),
            (NEUTRAL, "I don't agree or disagree"),
            (DISAGREE, "I disagree"),
            (STRONG_DISAGREE, "I strongly disagree"),
            (SKIP, "Skip"),
        )

    class ClinicVisitFrequency:
        MORE_ONCE_MONTH = "more_than_once_a_month"
        ONCE_MONTH = "once_a_month"
        ONCE_2_3_MONTHS = "once_2_3_months"
        ONCE_4_5_MONTHS = "once_4_5_months"
        ONCE_6_9_MONTHS = "once_6_9_months"
        NEVER = "never"
        SKIP = "skip"

        choices = (
            (MORE_ONCE_MONTH, "More than once a month"),
            (ONCE_MONTH, "Once a month"),
            (ONCE_2_3_MONTHS, "Once every  2 to 3 months"),
            (ONCE_4_5_MONTHS, "Once every  4 to 5 months"),
            (ONCE_6_9_MONTHS, "Once every 6 to 9 months"),
            (NEVER, "Never"),
            (SKIP, "Skip"),
        )

    class LiverFrequency:
        WEEK_2_3 = "2_3_times_week"
        ONCE_WEEK = "once_a_week"
        ONCE_MONTH = "once_a_month"
        LESS_ONCE_MONTH = "less_once_a_month"
        NEVER = "never"
        SKIP = "skip"

        choices = (
            (WEEK_2_3, "2-3 times a week"),
            (ONCE_WEEK, "Once a week"),
            (ONCE_MONTH, "Once a month"),
            (LESS_ONCE_MONTH, "Less than once a month"),
            (NEVER, "Never"),
            (SKIP, "Skip"),
        )

    class DangerSign1:
        WEIGHT_GAIN = "weight_gain"
        VAGINAL_BLEED = "vaginal_bleeding"
        NOSE_BLEED = "nose_bleeds"
        SKIP = "skip"

        choices = (
            (WEIGHT_GAIN, "Weight gain of 4-5 kilograms"),
            (VAGINAL_BLEED, "Vaginal bleeding"),
            (NOSE_BLEED, "Nose bleeds"),
            (SKIP, "Skip"),
        )

    class DangerSign2:
        SWOLLEN = "swollen_feet_legs"
        BLOAT = "bloating"
        GAS = "gas"
        SKIP = "skip"

        choices = (
            (SWOLLEN, "Swollen feet and legs even after sleep"),
            (BLOAT, "Bloating"),
            (GAS, "Gas"),
            (SKIP, "Skip"),
        )

    class MaritalStatus:
        NEVER_MARRIED = "never_married"
        MARRIED = "married"
        SEPARATED = "separated_or_divorced"
        WIDOWED = "widowed"
        PARTNER = "parter_or_boyfriend"
        SKIP = "skip"
        choices = (
            (NEVER_MARRIED, "Never married"),
            (MARRIED, "Married"),
            (SEPARATED, "Separated or divorced"),
            (WIDOWED, "Widowed"),
            (PARTNER, "Have a partner or boyfriend"),
            (SKIP, "Skip"),
        )

    class EducationLevel:
        LESS_GRADE_7 = "less_grade_7"
        BETWEEN_GRADE_7_12 = "between_grade_7_12"
        MATRIC = "matric"
        DIPLOMA = "diploma"
        DEGREE_OR_HIGHER = "degree_or_higher"
        SKIP = "skip"
        choices = (
            (LESS_GRADE_7, "Less than Grade 7"),
            (BETWEEN_GRADE_7_12, "Between Grades 7-12"),
            (MATRIC, "Matric"),
            (DIPLOMA, "Diploma"),
            (DEGREE_OR_HIGHER, "University degree or higher"),
            (SKIP, "Skip"),
        )

    msisdn = models.CharField(max_length=255, validators=[za_phone_number])
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=255, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)
    breastfeed = models.CharField(
        max_length=4, choices=YesNoSkip.choices, null=True, default=None
    )
    breastfeed_period = models.CharField(
        max_length=20, choices=BreastfeedPeriod.choices, null=True, default=None
    )
    vaccine_importance = models.CharField(
        max_length=20, choices=AgreeDisagree.choices, null=True, default=None
    )
    vaccine_benefits = models.CharField(
        max_length=20, choices=AgreeDisagree.choices, null=True, default=None
    )
    clinic_visit_frequency = models.CharField(
        max_length=25, choices=ClinicVisitFrequency.choices, null=True, default=None
    )
    vegetables = models.CharField(
        max_length=4, choices=YesNoSkip.choices, null=True, default=None
    )
    fruit = models.CharField(
        max_length=4, choices=YesNoSkip.choices, null=True, default=None
    )
    dairy = models.CharField(
        max_length=4, choices=YesNoSkip.choices, null=True, default=None
    )
    liver_frequency = models.CharField(
        max_length=20, choices=LiverFrequency.choices, null=True, default=None
    )
    danger_sign1 = models.CharField(
        max_length=20, choices=DangerSign1.choices, null=True, default=None
    )
    danger_sign2 = models.CharField(
        max_length=20, choices=DangerSign2.choices, null=True, default=None
    )
    marital_status = models.CharField(
        max_length=20, choices=MaritalStatus.choices, null=True, default=None
    )
    education_level = models.CharField(
        max_length=20, choices=EducationLevel.choices, null=True, default=None
    )
    airtime_sent = models.BooleanField(default=False)
    airtime_sent_at = models.DateTimeField(null=True)
