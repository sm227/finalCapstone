from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Comment, PollOption, PollVote
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.files.storage import default_storage
from django.conf import settings
import os
from django.db.models import Count, Sum
from django.http import StreamingHttpResponse
import time
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.utils import timezone
import module.koreainvestment as mojito
from login.models import UserProfile
from django.contrib import messages
import requests
from .models import Stock


@login_required
def post_comment(request, symbol):
    stock = get_object_or_404(Stock, symbol=symbol)
    if request.method == "POST":
        text = request.POST.get('comment_text')
        image = request.FILES.get('comment_image')
        is_poll = request.POST.get('is_poll') == 'true'

        # 댓글이나 이미지나 투표 중 하나라도 있으면 댓글 생성
        if text or image or is_poll:
            comment = Comment.objects.create(
                user=request.user,
                text=text if text else '',
                stock=stock,
                is_poll=is_poll
            )

            if image:
                comment.image = image
                comment.save()

            # 투표 옵션 처리
            if is_poll:
                poll_options = []
                index = 0
                while True:
                    option_text = request.POST.get(f'poll_option_{index}')
                    if not option_text:
                        break
                    poll_option = PollOption.objects.create(
                        comment=comment,
                        text=option_text,
                        votes=0
                    )
                    poll_options.append({
                        'id': poll_option.id,
                        'text': poll_option.text,
                        'votes': 0,
                        'percentage': 0
                    })
                    index += 1

            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'user': request.user.username,
                'user_id': request.user.id,
                'created_at': int(comment.created_at.timestamp()),
                'image_url': comment.image.url if comment.image else None,
                'is_poll': is_poll,
                'poll_options': poll_options if is_poll else None,
                'text': text
            })
    return JsonResponse({'success': False, 'message': '댓글 내용이나 이미지 또는 투표가 필요합니다.'})


@login_required
def vote_poll(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            comment_id = data.get('comment_id')
            option_id = data.get('option_id')

            # 옵션 가져오기
            option = get_object_or_404(PollOption, id=option_id)
            comment = option.comment

            # 이미 투표했는지 확인
            if PollVote.objects.filter(option__comment=comment, user=request.user).exists():
                return JsonResponse({'success': False, 'message': '이미 투표하셨습니다.'})

            # 투표 생성
            PollVote.objects.create(option=option, user=request.user)
            option.votes += 1
            option.save()

            # 전체 투표 수와 비율 계산
            total_votes = comment.poll_options.aggregate(total=Sum('votes'))['total']
            poll_options = []
            for opt in comment.poll_options.all():
                percentage = (opt.votes / total_votes * 100) if total_votes > 0 else 0
                poll_options.append({
                    'id': opt.id,
                    'text': opt.text,
                    'votes': opt.votes,
                    'percentage': round(percentage, 1)
                })

            return JsonResponse({
                'success': True,
                'poll_options': poll_options
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})


# 댓글 가져오기
# @login_required
def get_comments(request, symbol):
    stock = get_object_or_404(Stock, symbol=symbol)
    comments = Comment.objects.filter(stock=stock).order_by('-created_at')
    comments_data = []

    for comment in comments:
        comment_data = {
            'id': comment.id,
            'user': comment.user.username,
            'user_id': comment.user.id,
            'text': comment.text,
            'created_at': int(comment.created_at.timestamp()),
            'image_url': comment.image.url if comment.image else None,
            'total_likes': comment.total_likes(),
            'total_dislikes': comment.total_dislikes(),
            'liked': request.user in comment.likes.all() if request.user.is_authenticated else False,
            'is_poll': comment.is_poll
        }

        if comment.is_poll:
            total_votes = comment.poll_options.aggregate(total=Sum('votes'))['total'] or 0
            poll_options = []
            for option in comment.poll_options.all():
                percentage = (option.votes / total_votes * 100) if total_votes > 0 else 0
                poll_options.append({
                    'id': option.id,
                    'text': option.text,
                    'votes': option.votes,
                    'percentage': round(percentage, 1)
                })
            comment_data['poll_options'] = poll_options
            comment_data['user_voted'] = PollVote.objects.filter(
                option__comment=comment,
                user=request.user
            ).exists() if request.user.is_authenticated else False

        comments_data.append(comment_data)

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
                return match.group()  # 매칭된 숫자 환
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
        last_poll_votes = {
            option.id: option.votes
            for comment in Comment.objects.filter(is_poll=True)
            for option in comment.poll_options.all()
        }

        while True:
            current_comments = set(Comment.objects.values_list('id', 'user_id'))
            current_likes = {comment.id: comment.total_likes() for comment in Comment.objects.all()}
            current_poll_votes = {
                option.id: option.votes
                for comment in Comment.objects.filter(is_poll=True)
                for option in comment.poll_options.all()
            }

            # 새 댓글 확인
            new_comments = current_comments - last_comments
            if new_comments:
                for comment_id, user_id in new_comments:
                    if user_id != request.user.id:
                        yield f"data: new_comment\n\n"
                        break

            # 삭제된 댓글 확인
            deleted_comments = last_comments - current_comments
            if deleted_comments:
                for comment_id, _ in deleted_comments:
                    yield f"data: deleted_{comment_id}\n\n"

            # 좋아요 변경 확인
            for comment_id, current_like_count in current_likes.items():
                if comment_id in last_likes and last_likes[comment_id] != current_like_count:
                    yield f"data: like_{comment_id}_{current_like_count}\n\n"

            for option_id, current_votes in current_poll_votes.items():
                if option_id in last_poll_votes and last_poll_votes[option_id] != current_votes:
                    option = PollOption.objects.get(id=option_id)
                    comment = option.comment
                    total_votes = sum(opt.votes for opt in comment.poll_options.all())

                    poll_data = {
                        'comment_id': comment.id,
                        'poll_options': [
                            {
                                'id': opt.id,
                                'votes': opt.votes,
                                'percentage': round((opt.votes / total_votes * 100) if total_votes > 0 else 0, 1)
                            }
                            for opt in comment.poll_options.all()
                        ]
                    }
                    yield f"data: poll_{json.dumps(poll_data)}\n\n"
                    break

            last_comments = current_comments
            last_likes = current_likes
            last_poll_votes = current_poll_votes
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
                comment.likes.remove(request.user)
                liked = False
            else:
                if request.user in comment.dislikes.all():
                    comment.dislikes.remove(request.user)
                comment.likes.add(request.user)
                liked = True

            return JsonResponse({
                'success': True,
                'liked': liked,
                'total_likes': comment.total_likes(),
                'total_dislikes': comment.total_dislikes()
            })
        except Comment.DoesNotExist:
            return JsonResponse({'success': False, 'message': '댓글을 찾을 수 없습니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': '잘못된 요청입니다.'})


# 비추천
@login_required
def dislike_comment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            comment_id = data.get('comment_id')
            comment = Comment.objects.get(id=comment_id)

            if request.user in comment.dislikes.all():
                comment.dislikes.remove(request.user)
                disliked = False
            else:
                if request.user in comment.likes.all():
                    comment.likes.remove(request.user)
                comment.dislikes.add(request.user)
                disliked = True

            return JsonResponse({
                'success': True,
                'disliked': disliked,
                'total_dislikes': comment.total_dislikes(),
                'total_likes': comment.total_likes()
            })
        except Comment.DoesNotExist:
            return JsonResponse({'success': False, 'message': '댓글을 찾을 수 없습니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': '잘못된 요청'})


@login_required
def community(request, symbol):
    load_dotenv()
    temperature = float(get_hangang_temperature())

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        messages.error(request, "사용자 프로필을 찾을 수 없습니다. 관리자에게 문의하세요.")
        return redirect('login')

    broker = mojito.KoreaInvestment(
        api_key=user_profile.api_key,
        api_secret=user_profile.api_secret,
        acc_no=user_profile.acc_num,
        exchange='나스닥',
        mock=True
    )

    balance = broker.fetch_present_balance()
    test = broker.fetch_balance_oversea()
    stock_holdings = []

    # 주식 정보 수집
    for comp in test['output1']:
        stock_holdings.append({
            'symbol': comp['ovrs_pdno'],
            'name': comp['ovrs_item_name'],
            'amount': comp['ovrs_cblc_qty'],
            'exchange_code': comp['ovrs_excg_cd'],
            'profit_loss_rate': float(comp['evlu_pfls_rt']),
            'last_updated': timezone.now(),
        })

        # Stock 모델 생성 또는 업데이트
        stock, created = Stock.objects.get_or_create(
            symbol=comp['ovrs_pdno'],
            defaults={
                'name': comp['ovrs_item_name'],
                'price': 0.0
            }
        )

    # 수익률 기준으로 정렬하고 상위 5개만 선택
    stock_holdings.sort(key=lambda x: x['profit_loss_rate'], reverse=True)
    top_5_stocks = stock_holdings[:5]

    # 현재 선택된 주식 정보 가져오기
    stock = get_object_or_404(Stock, symbol=symbol)
    comments = Comment.objects.filter(stock=stock)

    context = {
        'symbol': symbol,
        'stock': stock,
        'comments': comments,
        'temperature': temperature,
        'stocks': top_5_stocks  # 변경된 부분: top 5 주식만 전달
    }

    comments_url = reverse('get_comments', kwargs={'symbol': symbol})
    context['comments_url'] = comments_url

    return render(request, 'community/community.html', context)


def check_like_status(request):
    comment_id = request.GET.get('comment_id')
    try:
        comment = Comment.objects.get(id=comment_id)
        liked = request.user in comment.likes.all() if request.user.is_authenticated else False
        return JsonResponse({'liked': liked})
    except Comment.DoesNotExist:
        return JsonResponse({'liked': False})
