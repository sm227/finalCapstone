# prediction/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # 예측 폼을 보여주는 페이지
    path('prediction/', views.predict_stock_price, name='prediction'),
]
