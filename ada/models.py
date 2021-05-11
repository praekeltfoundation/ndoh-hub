from django.db import models


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

    def __str__(self):
        if self.symptom_check_url:
            return (
                f"{self.parameter}: https://hub.momconnect.co.za/redirect/{self.id} \n"
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
                f"https://hub.momconnect.co.za/redirect with parameter \n"
                f"{self.symptom_check_url.parameter} \n"
                f"was visited at {self.time_stamp}"
            )
