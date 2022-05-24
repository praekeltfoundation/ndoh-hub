from django.db import models

from .validators import za_phone_number


class RedirectUrl(models.Model):

    content = models.TextField(
        default="This entry has no copy",
        help_text="The content of the mesage that this link was sent in",
    )
    symptom_check_url = models.URLField(
        max_length=200, blank=False, default="http://symptomcheck.co.za"
    )
    parameter = models.IntegerField(null=True)
    time_stamp = models.DateTimeField(auto_now=True)

    def my_counter(self):
        total_number = RedirectUrlsEntry.objects.filter(
            symptom_check_url=self.id
        ).count()
        return total_number

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("ada_hook", args=[str(self.id)])

    def __str__(self):
        if self.symptom_check_url:
            return (
                f"{self.parameter}: {self.get_absolute_url()} \n"
                f"| Clicked {self.my_counter()} times | Content: {self.content}"
            )


class RedirectUrlsEntry(models.Model):
    symptom_check_url = models.ForeignKey(
        RedirectUrl, on_delete=models.CASCADE, null=True
    )
    time_stamp = models.DateTimeField(auto_now=True)
    parameter = models.IntegerField(null=True)

    def __str__(self):
        if self.symptom_check_url:
            return (
                f"Url with parameter \n"
                f"{self.symptom_check_url.parameter} \n"
                f"was visited at {self.time_stamp}"
            )


class AdaSelfAssessment(models.Model):
    contact_id = models.UUIDField()
    msisdn = models.CharField(max_length=255, validators=[za_phone_number])
    assessment_id = models.UUIDField()
    step = models.IntegerField(null=True)
    optionId = models.IntegerField(null=True, blank=True)
    user_input = models.TextField(null=True, blank=True)
    title = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    choice = models.TextField(null=True, blank=True)
    pdf_media_id = models.CharField(max_length=255, null=True, blank=True)
    roadblock = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return (
            f"Contact_ID: {self.contact_id} | Step: {self.step} "
            f"| AssessmentID: {self.assessment_id} \n"
            f"| User_Input: {self.user_input} | Title: {self.title} \n"
            f"| Created_at: {self.created_at}"
        )
