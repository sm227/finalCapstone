from django.urls import path
from . import views

urlpatterns = [
    path('community/<str:symbol>/', views.community_symbol, name='community_symbol'),  # 종목별 커뮤니티
    # path('community/community/<str:symbol>/', views.community_symbol, name='community_symbol'),
    path('', views.community, name='community'),
    path('community/', views.community, name='community'),
    # path('comments/', views.get_comments, name='get_comments'),
    path('delete_comment/', views.delete_comment, name='delete_comment'),
    # path('comment/post/', views.post_comment, name='post_comment'),
    path('post_comment/<str:symbol>/', views.post_comment, name='post_comment'),  # 종목별 댓글 작성
    path('get_comments/<str:symbol>/', views.get_comments, name='get_comments'),  # 종목별 댓글 가져오기
]
