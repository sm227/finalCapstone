from . import views
from django.urls import path, include

urlpatterns = [
    path('', views.trading, name='trading'),
    path('trading/', views.trading, name='trading'),
    path('articles/', include('articles.urls')),
]