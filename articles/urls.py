# articles/urls.py

from django.urls import path
from . import views
from trading import views as trading_views

urlpatterns = [
    path('', views.articles, name='articles'),
    path('articles/', views.articles, name='articles'),
    path('summarize_article/', views.summarize_article, name='summarize_article'),
    path('trading/', trading_views.trading, name='trading'),
]