from django.db import models

class Car(models.Model):
    title = models.CharField(max_length=255)
    price = models.CharField(max_length=50)
    image_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title
