import os
from django.shortcuts import render
from dotenv import load_dotenv
from .models import Stock
from django.utils import timezone
import mojito
import time
from django.http import JsonResponse

def dashboard(request):
    load_dotenv()

    # 주식 API 데이터 가져오기
    broker = mojito.KoreaInvestment(
        api_key=os.getenv('api_key'),
        api_secret=os.getenv('api_secret'),
        acc_no=os.getenv('acc_no'),
        exchange='나스닥',
        mock=True
    )

    balance = broker.fetch_present_balance()
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
            'last_updated': timezone.now()
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

# 비동기 작업을 시작하는 함수
def start_long_task(request):
    # 작업을 시작할 때 세션에 진행 상태 초기화
    request.session['progress_status'] = 0

    # 시간이 오래 걸리는 작업 시뮬레이션
    for i in range(10):
        time.sleep(1)  # 각 단계마다 1초 대기
        request.session['progress_status'] = (i + 1) * 10  # 10%씩 진행
        request.session.modified = True  # 세션 변경을 알리기 위해 세션을 수정

    return JsonResponse({'status': 'Task started'})

# 진행 상태를 클라이언트에 전달하는 뷰
def get_progress_status(request):
    # 세션에 저장된 진행 상태를 반환
    progress_status = request.session.get('progress_status', 0)
    return JsonResponse({'progress': progress_status})
