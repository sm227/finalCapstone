# views.py
from django.shortcuts import render
import requests
import json


def index(request):
    if request.method == 'POST':
        company = request.POST.get('company', 'GOOG')
        time_diff = request.POST.get('time_diff', 'days')
        model_type = request.POST.get('model_type', 'RandomForestRegressor')

        # API 엔드포인트로 요청
        url = 'http://127.0.0.1:8005/api/predict'
        params = {
            'company': company,
            'time_diff_value': time_diff,
            'model_type': model_type
        }

        response = requests.post(url, params=params)
        if response.status_code == 200:
            prediction_data = response.json()
            return render(request, 'analytics/index.html', {
                'prediction_data': prediction_data,
                'company': company,
                'selected_time_diff': time_diff,
                'selected_model': model_type
            })

    # GET 요청이나 초기 로딩시
    return render(request, 'analytics/index.html', {
        'company': 'GOOG',
        'selected_time_diff': 'days',
        'selected_model': 'RandomForestRegressor'
    })


