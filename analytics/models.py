from django.db import models
from django.utils import timezone

class StockPrediction(models.Model):
    symbol = models.CharField(max_length=10)
    company_name = models.CharField(max_length=100)
    predicted_price = models.FloatField()
    actual_price = models.FloatField()
    prediction_date = models.DateTimeField(default=timezone.now)
    confidence_score = models.FloatField()
    
    class Meta:
        ordering = ['-prediction_date']

class PredictionMetrics(models.Model):
    prediction = models.ForeignKey(StockPrediction, on_delete=models.CASCADE)
    rmse = models.FloatField()
    mae = models.FloatField()
    mape = models.FloatField()
    accuracy = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
