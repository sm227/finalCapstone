# articles/urls.py

from django.urls import path, include
from . import views
from trading import views as trading_views

urlpatterns = [
    path('', views.articles_page, name='articles_page'),
    path('summarize_article/', views.summarize_article, name='summarize_article'),
    path('api/articles/', views.articles, name='articles'),
]
