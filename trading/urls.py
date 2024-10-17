from . import views
from django.urls import path, include

urlpatterns = [
    path('', views.trading, name='trading'),
    path('trading/', views.trading, name='trading'),
    path('place_order/', views.place_order, name='place_order'),
    path('articles/', include('articles.urls')),
]
