from django.db import models


class RedirectUrl(models.Model):

    url = models.URLField(
        max_length=255,
        blank=True,
        null=True,
        default="https://hub.momconnect.za/confirmredirect",
    )
    content = models.TextField(default="This entry has no copy")
    refresh_url = models.CharField(
        max_length=200, null=False, blank=False, default="http://127.0.0.1:8000"
    )
    symptom_check_url = models.CharField(
        max_length=200, null=False, blank=False, default="http://symptomcheck.co.za"
    )
    parameter = models.IntegerField(null=True, blank=True)
    time_stamp = models.DateTimeField(auto_now=True)

    def my_counter(self):
        total_number = RedirectUrlsEntry.objects.filter(url=self.id).count()
        return total_number

    def __str__(self):
        if self.url:
            return (f"{self.parameter}: {self.url}/{self.id} \n"
                    f"| Clicked {self.my_counter()} times | Content: {self.content}")


class RedirectUrlsEntry(models.Model):
    url = models.ForeignKey(
        RedirectUrl, on_delete=models.CASCADE, blank=True, null=True
    )
    time_stamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.url:
            return (f"{self.url.url} with ID {self.url.id} \n"
                    f"was visited at {self.time_stamp}")
