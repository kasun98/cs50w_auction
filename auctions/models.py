from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class User(AbstractUser):
    pass

class Item(models.Model):
    id = models.BigAutoField(primary_key=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()
    start_bid = models.DecimalField(max_digits=10, decimal_places=2)
    img_url = models.URLField(blank=True, null=True)
    category = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=1) #Y or N, Y for active, N for sold 
    created_at = models.DateTimeField(auto_now_add=True)

class Bid(models.Model):
    id = models.BigAutoField(primary_key=True)
    item_id = models.ForeignKey(Item, on_delete=models.CASCADE)
    n_bids = models.IntegerField(null=True)
    current_bidder_id = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    current_bid = models.DecimalField(max_digits=10, decimal_places=2)
    

class Comments(models.Model):
    id = models.BigAutoField(primary_key=True)
    item_id = models.ForeignKey(Item, on_delete=models.CASCADE)
    commenter_id = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.TextField()
    time = models.DateTimeField(auto_now_add=True)

class Watchlist(models.Model):
    id = models.BigAutoField(primary_key=True)
    uid = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    item_id = models.ForeignKey(Item, on_delete=models.CASCADE)
    watch = models.CharField(max_length=1) #Y or N, Y for yes, N for no
    time = models.DateTimeField(auto_now_add=True)

