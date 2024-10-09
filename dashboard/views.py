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
        mock=False
    )

    try:
        resp = broker.fetch_balance()
    except KeyError as e:
        # KeyError 발생 시 예외 처리
        print(f"KeyError: {e}. Please check the API response structure.")
        return render(request, 'dashboard/dashboard.html', {'error': str(e)})

        # 전체 응답 확인
    pprint.pprint(resp)  # API 응답 출력

    # 보유 종목 리스트 가공
    stock_holdings = []
    total_value = 0  # 기본값 설정

    # 보유 종목 데이터 처리
    if resp.get('output1'):  # 보유 종목이 있을 때
        for comp in resp['output1']:
            stock_holdings.append({
                'symbol': comp['pdno'],
                'name': comp['prdt_name'],
                'quantity': int(comp['hldg_qty']),
                'purchase_price': float(comp['pchs_amt']),
                'current_value': float(comp['evlu_amt']),
                'last_updated': timezone.now()
            })

    # total_value 계산
    if resp.get('output2') and resp['output2']:
        total_value = resp['output2'][0].get('tot_evlu_amt', 0)




    # total_value 계산
    # total_value = 0  # 기본값 설정
    # if 'output2' in resp and resp['output2']:
    #     total_value = resp['output2'][0].get('tot_evlu_amt', 0)
    #
    #     # tr_cont가 없는 경우 처리
    #     if 'tr_cont' not in resp['output2'][0]:
    #         print("Warning: 'tr_cont' is missing.")



    print(resp['output2'][0]['tot_evlu_amt'])
    pprint.pprint(resp)

    context = {
        'acc_no': "50117588-01",
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
    }

    #resp = broker.fetch_balance()
    #print(resp)  # 응답 내용 출력

    # test()
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
