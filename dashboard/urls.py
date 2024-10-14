# dashboard/urls.py
from django.urls import path, include
from . import views
from trading import views as trading_views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('articles/', include('articles.urls')),
    path('trading/', trading_views.trading, name='trading'),
]
