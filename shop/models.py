from django.db import models
from django.contrib.auth.models import User

class Car(models.Model):

    title = models.CharField(max_length=255)
    price = models.CharField(max_length=255)
    image_url = models.CharField(max_length=255)
    # stock = models.IntegerField()

    class Meta:
        managed = False  
        db_table = 'cars'  

    def __str__(self):
        return self.title

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"Cart of {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Car, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.title} - {self.quantity}"