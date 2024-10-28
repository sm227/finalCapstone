from django.shortcuts import render, redirect
import module.koreainvestment as mojito
from django.http import JsonResponse
from login.models import UserProfile
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import json
from django.contrib import messages

load_dotenv()


@login_required(login_url='login')
# Create your views here.
def portfolio(request):
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
        acc_no=user_profile.acc_num,  # 계좌 번호
        exchange='나스닥',
        mock=True
    )

    balance = broker.fetch_present_balance()
    test = broker.fetch_balance_oversea()
    print(balance)
    print("test: ", test)
    stock_holdings = []
    total_value = 0
    total_amount = 0

    for comp in test['output1']:
        amount = int(comp['ovrs_cblc_qty'])
        total_amount += amount
        stock_holdings.append({
            'symbol': comp['ovrs_pdno'],
            'name': comp['ovrs_item_name'],
            'amount': amount,
            'exchange_code': comp['ovrs_excg_cd'],
            'profit_loss_rate': float(comp['evlu_pfls_rt']),
            'last_updated': timezone.now(),
        })

    for stock in stock_holdings:
        stock['amount_percentage'] = (stock['amount'] / total_amount * 100) if total_amount > 0 else 0

    stock_holdings = sorted(stock_holdings, key=lambda x: x['amount_percentage'], reverse=True)

    total_value = balance['output3'].get('tot_asst_amt', 0)
    PnL = balance['output3'].get('tot_evlu_pfls_amt')

    colors = ['#5fc6e0', '#ffcf73', '#6fd667', '#ff6f6f', '#b57fd6', '#ff99b2', '#d1e866',
              '#73e8e6', '#b3ff73', '#ffa773', '#ff8c73', '#d67f9f', '#7373ff', '#c4ffe1',
              '#ff8e8a', '#6fcfe6', '#a9e8a1', '#ffffaa', '#cfa5b5', '#e8a5ff', '#d1e8cc',
              '#ffcb99', '#a5e8a5', '#ffdb88', '#8fe8e8', '#ff6677', '#73cde8']

    for i, stock in enumerate(stock_holdings):
        stock['color'] = colors[i % len(colors)]

    context = {
        'acc_no': user_profile.acc_num,
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
        'PnL': float(PnL)
    }

    return render(request, 'portfolio/portfolio.html', context)
