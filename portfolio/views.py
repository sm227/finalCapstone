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

    total_value = balance['output3'].get('tot_asst_amt', 0)
    PnL = balance['output3'].get('tot_evlu_pfls_amt')

    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22',
              '#17becf',
              '#393b79', '#637939', '#8c6d31', '#843c39', '#7b4173', '#5254a3', '#9c9ede', '#8ca252', '#bd9e39',
              '#ad494a',
              '#a55194', '#6b6ecf', '#b5cf6b', '#e7ba52', '#d6616b', '#ce6dbd', '#de9ed6', '#e7969c', '#9edae5',
              '#98df8a',
              '#ffbb78', '#ff9896', '#c5b0d5', '#c49c94', '#f7b6d2', '#dbdb8d', '#c7c7c7', '#aec7e8', '#ffbb78',
              '#98df8a',
              '#c59434', '#007f7f', '#ff3377', '#ff9f00', '#bfb300', '#0073bf', '#9933ff', '#00bf6f', '#e6194B',
              '#42d4f4']
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
