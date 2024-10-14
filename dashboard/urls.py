# dashboard/urls.py
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('articles/', include('articles.urls')),
    # path('ROI', views.ROI, name='ROI'),
]