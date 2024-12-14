from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    INVESTMENT_CHOICES = [
        ('conservative', '안정형'),
        ('balanced', '중립형'),
        ('aggressive', '공격형'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    api_key = models.CharField(max_length=200)
    api_secret = models.CharField(max_length=200)
    acc_num = models.CharField(max_length=100)
    investment_style = models.CharField(
        max_length=20, 
        choices=INVESTMENT_CHOICES,
        default='balanced'
    )
    auto_investment = models.BooleanField(default=False)
    total_investment = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    per_stock_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    compound_rate =  models.BooleanField(default=False)


    def __str__(self):
        return self.user.username