from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Comment
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.files.storage import default_storage
from django.conf import settings
import os
from django.db.models import Count
from django.http import StreamingHttpResponse
import time


@login_required
# 댓글 작성
def post_comment(request):
    if request.method == "POST":
        text = request.POST.get('comment_text')
        image = request.FILES.get('comment_image')

        if text or image:  # 텍스트나 이미지 중 하나라도 있으면 진행
            comment = Comment.objects.create(
                user=request.user,
                text=text if text else ''
            )

            if image:
                comment.image = image
                comment.save()

            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'user': request.user.username,
                'user_id': request.user.id,
                'created_at': int(comment.created_at.timestamp()),
                'image_url': comment.image.url if comment.image else None
            })
    return JsonResponse({'success': False, 'message': '댓글 내용이나 이미지가 필요합니다.'})


# 댓글 가져오기
def get_comments(request):
    comments = Comment.objects.all().order_by('-created_at')
    comments_data = []
    for comment in comments:
        comments_data.append({
            'id': comment.id,
            'user': comment.user.username,
            'user_id': comment.user.id,
            'text': comment.text,
            'created_at': int(comment.created_at.timestamp()),
            'image_url': comment.image.url if comment.image else None,
            'total_likes': comment.total_likes(),
            'liked': request.user in comment.likes.all() if request.user.is_authenticated else False
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


import re
from bs4 import BeautifulSoup
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from dotenv import load_dotenv
# from .models import Stock
from django.utils import timezone
import module.koreainvestment as mojito
from login.models import UserProfile
from django.contrib import messages
import requests


def get_hangang_temperature():
    url = 'https://hangang.life/'
    response = requests.get(url)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        temperature_element = soup.select_one('div.fullscreen > div > span:nth-child(1)')

        if temperature_element:
            # 텍스트에서 숫자 부분만 추출
            temperature_text = temperature_element.get_text().strip()
            match = re.search(r'[-+]?\d*\.\d+|\d+', temperature_text)  # 소수점 포함 숫자 추출
            if match:
                return match.group()  # 매칭된 숫자 ���환
            else:
                return "온도 데이터를 처리할 수 없습니다."
        else:
            return "온도 정보를 찾을 수 없습니다."
    else:
        return "웹사이트를 가져오는 데 실패했습니다."


# 댓글 갱신
def comment_stream(request):
    def event_stream():
        last_comments = set(Comment.objects.values_list('id', 'user_id'))
        last_likes = {comment.id: comment.total_likes() for comment in Comment.objects.all()}
        
        while True:
            current_comments = set(Comment.objects.values_list('id', 'user_id'))
            current_likes = {comment.id: comment.total_likes() for comment in Comment.objects.all()}
            
            # 새 댓글 확인
            new_comments = current_comments - last_comments
            if new_comments:
                for comment_id, user_id in new_comments:
                    if user_id != request.user.id:
                        yield f"data: new_comment\n\n"
                        break
            

            deleted_comments = last_comments - current_comments
            if deleted_comments:
                for comment_id, _ in deleted_comments:
                    yield f"data: deleted_{comment_id}\n\n"
            

            for comment_id, current_like_count in current_likes.items():
                if comment_id in last_likes and last_likes[comment_id] != current_like_count:
                    yield f"data: like_{comment_id}_{current_like_count}\n\n"
            
            last_comments = current_comments
            last_likes = current_likes
            time.sleep(1)

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# 추천/
@login_required
def like_comment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            comment_id = data.get('comment_id')
            comment = Comment.objects.get(id=comment_id)

            if request.user in comment.likes.all():
                # 이미 추천한 경우 추천 취소
                comment.likes.remove(request.user)
                liked = False
            else:
                # 추천하지 않은 경우 추천 추가
                comment.likes.add(request.user)
                liked = True

            return JsonResponse({
                'success': True,
                'liked': liked,
                'total_likes': comment.total_likes()
            })
        except Comment.DoesNotExist:
            return JsonResponse({'success': False, 'message': '댓글을 찾을 수 없습니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})


@login_required
def community(request):
    load_dotenv()
    temperature = float(get_hangang_temperature())  # 한강 물 온도 가져오기

    # 현재 로그인한 사용자의 UserProfile 가져오기
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # UserProfile이 없는 경우 에러 처리
        messages.error(request, "사용자 프로필을 찾을 수 없습니다. 관리자에게 문의하세요.")
        return redirect('login')

    # 주식 API 데이터 가져오기
    broker = mojito.KoreaInvestment(
        api_key=user_profile.api_key,
        api_secret=user_profile.api_secret,
        acc_no=user_profile.acc_num,
        exchange='나스닥',
        mock=True
    )

    balance = broker.fetch_present_balance()
    test = broker.fetch_balance_oversea()
    print(balance)

    stock_holdings = []

    for comp in test['output1']:
        stock_holdings.append({
            'symbol': comp['ovrs_pdno'],
            'name': comp['ovrs_item_name'],
            'amount': comp['ovrs_cblc_qty'],
            'exchange_code': comp['ovrs_excg_cd'],
            'profit_loss_rate': float(comp['evlu_pfls_rt']),
            'last_updated': timezone.now(),
        })
    top_5_stocks = sorted(stock_holdings, key=lambda x: x['profit_loss_rate'], reverse=True)[:5]

    total_value = balance['output3'].get('tot_asst_amt', 0)
    PnL = balance['output3'].get('tot_evlu_pfls_amt')

    # 모든 데이터를 하나의 딕셔너리에 포함
    context = {
        'acc_no': user_profile.acc_num,
        'stocks': top_5_stocks,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
        'PnL': float(PnL),
        'temperature': temperature  # 한강 물 온도 추가
    }

    return render(request, 'community/community.html', context)


def check_like_status(request):
    comment_id = request.GET.get('comment_id')
    try:
        comment = Comment.objects.get(id=comment_id)
        liked = request.user in comment.likes.all() if request.user.is_authenticated else False
        return JsonResponse({'liked': liked})
    except Comment.DoesNotExist:
        return JsonResponse({'liked': False})
