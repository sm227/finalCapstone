# articles/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.articles, name='articles'),
    path('summarize_article/', views.summarize_article, name='summarize_article'),
]
