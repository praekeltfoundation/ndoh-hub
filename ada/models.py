from django.db import models

# Create your models here.


class RedirectUrl(models.Model):

    urls = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField(default='This url has no copy')
    time_stamp = models.DateTimeField(auto_now=True)

    def my_counter(self):
        total_number = RedirectUrlsEntry.objects.filter(urls=self.id).count()
        return total_number

    def __str__(self):
        if self.urls:
            return f'ID - {self.id} for {self.urls}/{self.id} | Clicked {self.my_counter()} times | Content: {self.content}'


class RedirectUrlsEntry(models.Model):
    urls = models.ForeignKey(RedirectUrl,
                             on_delete=models.CASCADE, blank=True, null=True)
    time_stamp = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.urls:
            return f'{self.urls.urls} with ID {self.urls.id}  was visited at {self.time_stamp}'
