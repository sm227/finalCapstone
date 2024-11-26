from django.urls import path, include
from . import views
from trading import views as trading_views

urlpatterns = [
    path('', views.community, name='community'),
    path('community/', views.community, name='community'),
]
