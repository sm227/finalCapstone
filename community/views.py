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


@login_required
# 댓글 작성
def post_comment(request):
    if request.method == "POST":
        text = request.POST.get('comment_text')  # 댓글 내용
        image = request.FILES.get('comment_image') #이미지

        image_url = None


        if text:
            comment = Comment.objects.create(user=request.user, text=text)
            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'user': request.user.username,
                'user_id': request.user.id,
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
            'user_id': comment.user.id,
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
                return match.group()  # 매칭된 숫자 반환
            else:
                return "온도 데이터를 처리할 수 없습니다."
        else:
            return "온도 정보를 찾을 수 없습니다."
    else:
        return "웹사이트를 가져오는 데 실패했습니다."
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
