from django.urls import path
from . import views

urlpatterns = [
    # path('community/<str:symbol>/', views.community_symbol, name='community_symbol'),
    path('', views.community, name='community'),
    path('community/<str:symbol>/', views.community, name='community'),
    path('delete_comment/', views.delete_comment, name='delete_comment'),
    # path('comment/post/<str:symbol>/', views.post_comment, name='post_comment'),
    path('post_comment/<str:symbol>/', views.post_comment, name='post_comment'),
    path('get_comments/<str:symbol>/', views.get_comments, name='get_comments'),
    path('comment-stream/', views.comment_stream, name='comment_stream'),
    path('like-comment/', views.like_comment, name='like_comment'),
    path('dislike-comment/', views.dislike_comment, name='dislike_comment'),
    path('check-like-status/', views.check_like_status, name='check_like_status'),
    path('vote_poll/', views.vote_poll, name='vote_poll'),
]
