from django.urls import path
from . import views

urlpatterns = [
    path('', views.community, name='community'),
    path('community/', views.community, name='community'),
    path('comments/', views.get_comments, name='get_comments'),
    path('delete_comment/', views.delete_comment, name='delete_comment'),
    path('comment/post/', views.post_comment, name='post_comment'),
]
