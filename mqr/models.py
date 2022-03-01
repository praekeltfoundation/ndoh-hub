from django.db import models


class MqrStrata(models.Model):
    province = models.CharField(max_length=25, null=False, blank=False)
    weeks_pregnant = models.CharField(max_length=12, null=False, blank=False)
    age = models.IntegerField(null=False, blank=False)
    next_index = models.IntegerField(default=0, null=False, blank=False)
    order = models.CharField(max_length=50, null=False, blank=False)
