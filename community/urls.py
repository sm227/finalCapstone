from django.urls import path
from . import views

urlpatterns = [
    path('', views.community, name='community'),
    path('community/', views.community, name='community'),
    path('comments/', views.get_comments, name='get_comments'),
    path('delete_comment/', views.delete_comment, name='delete_comment'),
    path('comment/post/', views.post_comment, name='post_comment'),
    path('comment-stream/', views.comment_stream, name='comment_stream'),
    path('like-comment/', views.like_comment, name='like_comment'),
    path('check-like-status/', views.check_like_status, name='check_like_status'),
]
