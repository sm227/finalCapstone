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
import yfinance as yf
from random import shuffle

load_dotenv()

def fetch_stock_news(symbol):
    try:
        ticker = yf.Ticker(symbol)
        
        news_data = []
        for news in ticker.news[:20]:
            published_time = timezone.datetime.fromtimestamp(news['providerPublishTime'])
            
            news_data.append({
                'symbol': symbol,
                'title': news['title'],
                'link': news['link'],
                'published': published_time,
                'thumbnail': news.get('thumbnail', {}).get('resolutions', [{}])[0].get('url', '')
            })
            
        print(f"Found {len(news_data)} news items for {symbol}")
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

    # 수익률 기준으로 정렬
    stock_holdings = sorted(stock_holdings, key=lambda x: x['profit_loss_rate'], reverse=True)

    # 정렬 후 퍼센티지 계산
    for stock in stock_holdings:
        stock['amount_percentage'] = (stock['amount'] / total_amount * 100) if total_amount > 0 else 0

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
        for future, stock in zip(news_futures, stock_holdings):
            news_items = future.result()
            # 각 뉴스 항목에 수익률 정보 추가
            for news in news_items:
                news['profit_loss_rate'] = stock['profit_loss_rate']
            all_news.extend(news_items)

    shuffle(all_news)

    context = {
        'acc_no': user_profile.acc_num,
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
        'PnL': float(PnL),
        'stock_news': all_news
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
            # 정렬 제거하고 그대로 사용
            stock_holdings = [
                {'symbol': comp['ovrs_pdno'], 'profit_loss_rate': float(comp['evlu_pfls_rt'])} 
                for comp in test['output1']
            ]
            # 랜덤으로 섞기
            shuffle(stock_holdings)
            
            total_stocks = len(stock_holdings)

            for idx, stock in enumerate(stock_holdings, 1):
                progress = (idx / total_stocks) * 100
                news_data = fetch_stock_news(stock['symbol'])
                for news in news_data:
                    news['profit_loss_rate'] = stock['profit_loss_rate']

                data = {
                    'progress': progress,
                    'message': f'뉴스를 불러오는 중... ({idx}/{total_stocks})',
                    'news': news_data
                }

                yield f"data: {json.dumps(data)}\n\n"
                time.sleep(0.1)

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