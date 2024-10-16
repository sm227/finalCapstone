# articles/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.articles_page, name='articles_page'),
    path('summarize_article/', views.summarize_article, name='summarize_article'),
    path('api/articles/', views.articles, name='articles'),
]
