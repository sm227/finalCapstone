from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from login.models import UserProfile
from .models import StockPrediction, PredictionMetrics
from algo import EnhancedStockPredictor
import json

import module.koreainvestment as mojito

@login_required
def analytics_dashboard(request):
    return render(request, 'analytics/index.html')
