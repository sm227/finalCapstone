from django.db import models
from datetime import datetime

# 추천 모델 정의
class StockRecommendation(models.Model):
    symbol = models.CharField(max_length=10)
    action = models.CharField(max_length=10)
    reason = models.TextField()
    price_target = models.FloatField()
    stop_loss = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    compound_rate = models.BooleanField(default=False)
    compound_interest = models.FloatField()

