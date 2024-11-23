from django.contrib import admin
from .models import StockPrediction, PredictionMetrics

@admin.register(StockPrediction)
class StockPredictionAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'company_name', 'predicted_price', 'actual_price', 'prediction_date']
    search_fields = ['symbol', 'company_name']

@admin.register(PredictionMetrics)
class PredictionMetricsAdmin(admin.ModelAdmin):
    list_display = ['prediction', 'rmse', 'mae', 'mape', 'accuracy', 'created_at']
