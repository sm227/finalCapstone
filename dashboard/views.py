import os

from bs4 import BeautifulSoup
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from dotenv import load_dotenv
from .models import Stock
from django.utils import timezone
import module.koreainvestment as mojito
from login.models import UserProfile
from django.contrib import messages
import requests
from analytics2.models import StockRecommendation
from community.models import Stock

@login_required(login_url='login')
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
        acc_no=user_profile.acc_num,  # acc_no는 여전히 환경 변수에서 가져옵니다.
        exchange='나스닥',
        mock=True
    )

    balance = broker.fetch_present_balance()
    print(balance)
    stock_holdings = []
    total_value = 0

    # AI 추천 종목 목록 가져오기
    ai_recommendations = StockRecommendation.objects.values_list('symbol', flat=True)

    for comp in balance['output1']:
        # Stock 모델에 데이터 추가 또는 존재 시 업데이트
        stock, created = Stock.objects.get_or_create(
            symbol=comp['pdno'],
            defaults={
                'name': comp['prdt_name'],
                'price': float(comp['frcr_pchs_amt']),
            }
        )

        stock_holdings.append({
            'symbol': comp['pdno'],
            'name': comp['prdt_name'],
            'country': comp['natn_kor_name'],
            'exchange_code': comp['ovrs_excg_cd'],
            'market_name': comp['tr_mket_name'],
            'profit_loss_rate': float(comp['evlu_pfls_rt1']),
            'exchange_rate': float(comp['bass_exrt']),
            'unit_amt': float(comp['frcr_pchs_amt']),
            'last_updated': timezone.now(),
            'is_ai_recommended': comp['pdno'] in ai_recommendations
        })

    total_value = balance['output3'].get('tot_asst_amt', 0)
    PnL = balance['output3'].get('tot_evlu_pfls_amt')
    cpi_data = crawl_cpi_data()
    ppi_data = crawl_ppi_data()

    cpi_data = crawl_cpi_data()

    # AI 추천 종목 수와 정확도 계산
    ai_recommended_stocks = [stock for stock in stock_holdings if stock['is_ai_recommended']]
    ai_recommendations_count = len(ai_recommended_stocks)
    
    # 수익이 발생한 AI 추천 종목 수 계산
    profitable_ai_stocks = [stock for stock in ai_recommended_stocks if stock['profit_loss_rate'] > 0]
    ai_accuracy = (len(profitable_ai_stocks) / ai_recommendations_count * 100) if ai_recommendations_count > 0 else 0

    context = {
        'acc_no': user_profile.acc_num,
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
        'PnL': float(PnL),
        'cpi_data': cpi_data,
        'ppi_data': ppi_data,
        'ai_recommendations_count': ai_recommendations_count,  # 추가
        'ai_accuracy': round(ai_accuracy, 1)  # 추가 (소수점 첫째자리까지 표시)
    }

    return render(request, 'dashboard/dashboard.html', context)


def crawl_cpi_data():
    url = "https://kr.investing.com/economic-calendar/cpi-733"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # ID가 'eventHistoryTable733'인 테이블을 선택합니다.
    table = soup.select_one('#eventHistoryTable733')
    table_rows = table.select('tr') if table else []

    cpi_data = []
    for row in table_rows:
        cells = row.find_all('td')
        if len(cells) >= 5:
            publish_date = cells[0].get_text(strip=True)
            time = cells[1].get_text(strip=True)
            actual = cells[2].get_text(strip=True)
            forecast = cells[3].get_text(strip=True)
            previous = cells[4].get_text(strip=True)

            cpi_data.append({
                'publish_date': publish_date,
                'time': time,
                'actual': actual,
                'forecast': forecast,
                'previous': previous
            })

    return cpi_data

data = crawl_cpi_data()
#print("cpi")
# for item in data:
#     print(item)


def crawl_ppi_data():
    url = "https://kr.investing.com/economic-calendar/ppi-238"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.select_one('#eventHistoryTable238')
    table_rows = table.select('tr') if table else []

    ppi_data = []
    for row in table_rows:
        cells = row.find_all('td')
        if len(cells) >= 5:
            publish_date = cells[0].get_text(strip=True)
            time = cells[1].get_text(strip=True)
            actual = cells[2].get_text(strip=True)
            forecast = cells[3].get_text(strip=True)
            previous = cells[4].get_text(strip=True)

            ppi_data.append({
                'publish_date': publish_date,
                'time': time,
                'actual': actual,
                'forecast': forecast,
                'previous': previous
            })

    return ppi_data

data = crawl_ppi_data()
#print("ppi")
# for item in data:
#     print(item)