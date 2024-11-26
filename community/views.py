from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Comment
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import json


@login_required
# 댓글 작성
def post_comment(request):
    if request.method == "POST":
        text = request.POST.get('comment_text')  # 댓글 내용
        if text:
            comment = Comment.objects.create(user=request.user, text=text)
            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'user': request.user.username,
                'created_at': int(comment.created_at.timestamp())  # Unix 타임스탬프
            })
    return JsonResponse({'success': False, 'message': '댓글 내용이 없습니다.'})


# 댓글 가져오기
def get_comments(request):
    comments = Comment.objects.all().order_by('-created_at')
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'user': comment.user.username,
            'text': comment.text,
            'created_at': int(comment.created_at.timestamp()),  # Unix 타임스탬프
        })
    return JsonResponse({'comments': comments_data})


@login_required
# 댓글 삭제
def delete_comment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            comment_id = data.get('id')
            comment = Comment.objects.get(id=comment_id, user=request.user)
            comment.delete()
            return JsonResponse({'success': True})
        except Comment.DoesNotExist:
            return JsonResponse({'success': False, 'message': '댓글을 찾을 수 없습니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})


@login_required
def community(request):
    return render(request, 'community/community.html')
