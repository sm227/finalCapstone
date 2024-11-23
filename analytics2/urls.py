from django.urls import path
from . import views


app_name = "analytics2"
urlpatterns = [
    path('', views.index, name='index'),
    path('stock-analysis/', views.stock_analysis, name='stock_analysis'),
]
