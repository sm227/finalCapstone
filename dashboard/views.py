# dashboard/views.py
import os

from django.shortcuts import render
from dotenv import load_dotenv

from .models import Stock
from django.utils import timezone
import mojito
import pprint


def dashboard(request):
    load_dotenv()

    # 임시 데이터 생성
    # mock_stocks = [
    #     {'symbol': 'AAPL', 'name': 'Apple Inc.', 'current_price': 150.25, 'last_updated': timezone.now()},
    #     {'symbol': 'GOOGL', 'name': 'Alphabet Inc.', 'current_price': 2750.80, 'last_updated': timezone.now()},
    #     {'symbol': 'MSFT', 'name': 'Microsoft Corporation', 'current_price': 305.50, 'last_updated': timezone.now()},
    #     {'symbol': 'AMZN', 'name': 'Amazon.com Inc.', 'current_price': 3380.75, 'last_updated': timezone.now()},
    #     {'symbol': 'FB', 'name': 'Facebook, Inc.', 'current_price': 330.20, 'last_updated': timezone.now()},
    # ]

    # 총 포트폴리오 가치 계산
    # total_value = sum(stock['current_price'] for stock in mock_stocks)

    broker = mojito.KoreaInvestment(
        api_key=os.getenv('api_key'),
        api_secret=os.getenv('api_secret'),
        acc_no=os.getenv('acc_no'),
        exchange='나스닥',
        mock=True
    )

    balance = broker.fetch_present_balance()
    pprint.pprint(balance)

    # 보유 종목 리스트 가공
    stock_holdings = []
    total_value = 0  # 기본값 설정

    # 보유 종목 데이터 처리
    for comp in balance['output1']:
        stock_holdings.append({
            'symbol': comp['pdno'],
            'name': comp['prdt_name'],
            'country': comp['natn_kor_name'],  # 국가 정보 추가
            'exchange_code': comp['ovrs_excg_cd'],  # 거래소 코드 추가
            'market_name': comp['tr_mket_name'],  # 시장 이름 추가
            'profit_loss_rate': float(comp['evlu_pfls_rt1']),  # 평가손익률 추가
            'exchange_rate': float(comp['bass_exrt']),  # 기준 환율 추가
            'purchase_amount_foreign': float(comp['frcr_pchs_amt']),  # 외화 매입 금액 추가
            'last_updated': timezone.now()
        })

    total_value = balance['output3'].get('tot_asst_amt', 0)  # 자산

    total_profit_loss = balance['output3'].get('tot_evlu_pfls_amt', 0)  # 총 평가손익 금액

    context = {
        'acc_no': "50117588-01",
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
    }

    return render(request, 'dashboard/dashboard.html', context)

# def test():
#
#
#     # with open("../../koreainvestment.key") as f:
#     #     lines = f.readlines()
#     #
#     # key = lines[0].strip()
#     # secret = lines[1].strip()
#     # acc_no = lines[2].strip()
#
#     broker = mojito.KoreaInvestment(
#         api_key="PS2osgVtJebLijhOGFbRwYiw9lKwXQfK8PEk",
#         api_secret="TcmO8QRKiSVA+ZQIV8+mXXYdbPM1iMVZrChj5X4Pi83EhBV2YLlPDnWsn5zfi3OCLyQ1quEoBYpH262PxWlbSVPuA7YaSR5MGGnE9/cCter0+CY9jfGH/sbkdIgF/fCjgi5zKLg1J84lpuAy+Dr6UCAWfvtnkXLnkZuPKB5Jz+gsmp/arVE=",
#         acc_no="50117588-01"
#     )
#     resp = broker.fetch_balance()
#     pprint.pprint(resp)
