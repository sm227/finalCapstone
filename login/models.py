from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    api_key = models.CharField(max_length=200)
    api_secret = models.CharField(max_length=200)
    acc_num = models.CharField(max_length=100)


    def __str__(self):
        return self.user.username