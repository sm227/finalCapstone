from django.db import models

# Create your models here.
class StockPrediction(models.Model):
    company = models.CharField(max_length=10)
    prediction_date = models.DateTimeField(auto_now_add=True)
    actual_price = models.FloatField()
    predicted_price = models.FloatField()
    model_type = models.CharField(max_length=50)

    class Meta:
        ordering = ['-prediction_date']