from django.shortcuts import render, redirect
import module.koreainvestment as mojito
from django.http import JsonResponse, StreamingHttpResponse
from login.models import UserProfile
from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import timedelta
import json
from django.contrib import messages
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from django.core.paginator import Paginator
import time

load_dotenv()


def fetch_stock_news(symbol):
    try:
        url = f"https://finance.yahoo.com/quote/{symbol}/news"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # 새로운 선택자 사용
        news_items = soup.select('h3.clamp')  # class가 'clamp'인 h3 태그 선택
        print(f"Found {len(news_items)} news items for {symbol}")  # 디버깅용

        news_data = []
        for item in news_items[:5]:
            link_element = item.find_parent('a')  # 상위 a 태그 찾기
            if link_element:
                news_data.append({
                    'symbol': symbol,
                    'title': item.text.strip(),
                    'link': link_element.get('href', '')
                })

        return news_data

    except Exception as e:
        print(f"Error fetching news for {symbol}: {str(e)}")
        return []


@login_required(login_url='login')
def portfolio(request):
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

    all_news = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        news_futures = [executor.submit(fetch_stock_news, stock['symbol']) for stock in stock_holdings]
        for future in news_futures:
            all_news.extend(future.result())

        # 페이지네이션 추가
    paginator = Paginator(all_news, 5)  # 페이지당 5개 뉴스
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'acc_no': user_profile.acc_num,
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
        'PnL': float(PnL),
        'stock_news': page_obj
    }
    print(all_news)

    return render(request, 'portfolio/portfolio.html', context)


@login_required
def fetch_portfolio_news(request):
    def generate_news():
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            broker = mojito.KoreaInvestment(
                api_key=user_profile.api_key,
                api_secret=user_profile.api_secret,
                acc_no=user_profile.acc_num,
                exchange='나스닥',
                mock=True
            )
            
            test = broker.fetch_balance_oversea()
            stock_holdings = [comp['ovrs_pdno'] for comp in test['output1']]
            total_stocks = len(stock_holdings)
            
            for idx, symbol in enumerate(stock_holdings, 1):
                progress = (idx / total_stocks) * 100
                news_data = fetch_stock_news(symbol)
                
                data = {
                    'progress': progress,
                    'message': f'뉴스를 불러오는 중... ({idx}/{total_stocks})',
                    'news': news_data
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(0.5)  # 서버 부하 방지
                
        except Exception as e:
            error_data = {
                'error': str(e),
                'progress': 100,
                'message': '오류가 발생했습니다.'
            }
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingHttpResponse(
        generate_news(),
        content_type='text/event-stream'
    )