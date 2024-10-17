from . import views
from django.urls import path, include

urlpatterns = [
    path('', views.trading, name='trading'),
    path('trading/', views.trading, name='trading'),
    path('place_order/', views.place_order, name='place_order'),
    path('place_order_sell', views.place_order_sell, name='place_order_sell'),
    path('articles/', include('articles.urls')),
]
