import os

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from dotenv import load_dotenv
from .models import Stock
from django.utils import timezone
import mojito
from login.models import UserProfile
from django.contrib import messages

@login_required
def dashboard(request):
    load_dotenv()

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
        acc_no=os.getenv('acc_no'),  # acc_no는 여전히 환경 변수에서 가져옵니다.
        exchange='나스닥',
        mock=True
    )

    balance = broker.fetch_present_balance()
    print(balance)
    stock_holdings = []
    total_value = 0

    for comp in balance['output1']:
        stock_holdings.append({
            'symbol': comp['pdno'],
            'name': comp['prdt_name'],
            'country': comp['natn_kor_name'],
            'exchange_code': comp['ovrs_excg_cd'],
            'market_name': comp['tr_mket_name'],
            'profit_loss_rate': float(comp['evlu_pfls_rt1']),
            'exchange_rate': float(comp['bass_exrt']),
            'purchase_amount_foreign': float(comp['frcr_pchs_amt']),
            'last_updated': timezone.now(),
        })

    total_value = balance['output3'].get('tot_asst_amt', 0)
    PnL = balance['output3'].get('tot_evlu_pfls_amt')

    context = {
        'acc_no': os.getenv('acc_no'),
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
        'PnL': float(PnL)
    }

    return render(request, 'dashboard/dashboard.html', context)


# def ROI(request):
#     return render(request,"dashboard/views.py")
