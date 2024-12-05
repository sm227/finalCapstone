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
from module.koreainvestment import CURRENCY_CODE
import concurrent.futures
import pandas as pd
from django.core.cache import cache

load_dotenv()


def fetch_stock_news(symbol, ticker=None):
    try:
        ticker = yf.Ticker(symbol)
        news_data = []
        for news in ticker.news[:5]:
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


def fetch_stock_price(comp, ticker=None):
    """티커 객체를 재사용하도록 수정"""
    try:
        if not ticker:
            ticker = yf.Ticker(comp['ovrs_pdno'])

        price_options = [
            ticker.info.get('regularMarketPrice'),
            ticker.info.get('currentPrice'),
            ticker.info.get('previousClose'),
            ticker.fast_info.get('lastPrice')
        ]
        current_price = next((price for price in price_options if price is not None), None)
        return float(current_price) if current_price else float(comp.get('now_pric', 0))
    except Exception:
        return float(comp.get('now_pric', 0))


# 배당일 캘린더 삽입, 배당금 계산
def get_dividend_calendar(stocks, tickers=None):
    dividend_data = []
    for stock in stocks:
        try:
            ticker = yf.Ticker(stock['symbol'])
            # 배당 정보 가져오기
            dividends = ticker.dividends
            if not dividends.empty:
                dividends.index = dividends.index.tz_localize(None)

                # 최근 1년간의 배당금 합계 계산
                one_year_ago = pd.Timestamp.now().tz_localize(None) - pd.DateOffset(years=1)
                annual_dividends = dividends[dividends.index > one_year_ago]
                annual_dividend_total = float(annual_dividends.sum())  # 연간 총 배당금
                latest_date = dividends.index[-1]  # 마지막 배당일

                # 다음 배당 예상일
                next_dividend_date = latest_date + pd.DateOffset(years=1)

                # 배당 주기 계산 (연간 배당 횟수)
                dividend_frequency = len(annual_dividends)
                if dividend_frequency == 0:
                    dividend_frequency = len(dividends[-4:])  # 데이터가 부족한 경우 최근 4개 사용

                # 1회 배당금
                dividend_per_payment = annual_dividend_total / dividend_frequency if dividend_frequency > 0 else 0

                dividend_data.append({
                    'symbol': stock['symbol'],
                    'name': stock['name'],
                    'annual_dividend': annual_dividend_total,  # 연간 총 배당금
                    'dividend_per_payment': dividend_per_payment,  # 1회 배당금
                    'dividend_frequency': dividend_frequency,  # 연간 배당 횟수
                    'last_dividend_date': latest_date,
                    'expected_next_date': next_dividend_date,
                    'dividend_yield': ticker.info.get('dividendYield', 0) * 100 if ticker.info.get(
                        'dividendYield') else 0,
                    'amount': stock['amount'],
                    'logo_url': get_company_logo(stock['symbol'])
                })
        except Exception as e:
            print(f"Error fetching dividend data for {stock['symbol']}: {str(e)}")
            continue

    # 다음 배당일 기준으로 정렬
    dividend_data.sort(key=lambda x: x['expected_next_date'])
    return dividend_data


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

    # 캐시 키 설정
    cache_key = f"portfolio_data_{user_profile.user.id}"
    cached_data = cache.get(cache_key)

    if cached_data:
        return render(request, 'portfolio/portfolio.html', cached_data)

    balance = broker.fetch_present_balance()
    test = broker.fetch_balance_oversea()
    stock_holdings = []
    total_market_value = 0
    tickers = {}  # 티커 객체 재사용

    # 한 번에 모든 주식의 티커 객체 생성
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_symbol = {
            executor.submit(yf.Ticker, comp['ovrs_pdno']): comp['ovrs_pdno']
            for comp in test['output1']
        }
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                tickers[symbol] = future.result()
            except Exception as e:
                print(f"Error creating ticker for {symbol}: {str(e)}")

    # 주식 정보 처리
    for comp in test['output1']:
        symbol = comp['ovrs_pdno']
        ticker = tickers.get(symbol)
        if not ticker:
            continue

        try:
            current_price = fetch_stock_price(comp, ticker)
            amount = int(comp['ovrs_cblc_qty'])
            market_value = current_price * amount
            total_market_value += market_value

            stock_data = {
                'symbol': symbol,
                'name': comp['ovrs_item_name'],
                'amount': amount,
                'exchange_code': comp['ovrs_excg_cd'],
                'profit_loss_rate': float(comp['evlu_pfls_rt']),
                'current_price': current_price,
                'purchase_price': float(comp['pchs_avg_pric']),
                'currency': CURRENCY_CODE.get(comp['ovrs_excg_cd'], 'USD'),
                'last_updated': timezone.now(),
                'market_value': market_value,
                'logo_url': get_company_logo(symbol),
                'sector': ticker.info.get('sector', '기타')
            }
            stock_holdings.append(stock_data)
        except Exception as e:
            print(f"Error processing stock {symbol}: {str(e)}")
            continue

    # 수익률 기준으로 정렬 및 퍼센티지 계산
    stock_holdings = sorted(stock_holdings, key=lambda x: x['profit_loss_rate'], reverse=True)
    for stock in stock_holdings:
        stock['amount_percentage'] = (stock['market_value'] / total_market_value * 100) if total_market_value > 0 else 0

    # 차트 색상 할당
    colors = ['#5fc6e0', '#ffcf73', '#6fd667', '#ff6f6f', '#b57fd6', '#ff99b2', '#d1e866',
              '#73e8e6', '#b3ff73', '#ffa773', '#ff8c73', '#d67f9f', '#7373ff', '#c4ffe1',
              '#ff8e8a', '#6fcfe6', '#a9e8a1', '#ffffaa', '#cfa5b5', '#e8a5ff', '#d1e8cc',
              '#ffcb99', '#a5e8a5', '#ffdb88', '#8fe8e8', '#ff6677', '#73cde8']

    for i, stock in enumerate(stock_holdings):
        stock['color'] = colors[i % len(colors)]

    # 뉴스 데이터 가져오기 (병렬 처리)
    all_news = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        news_futures = [executor.submit(fetch_stock_news, stock['symbol'], tickers.get(stock['symbol']))
                        for stock in stock_holdings]
        for future, stock in zip(news_futures, stock_holdings):
            news_items = future.result()
            for news in news_items:
                news['profit_loss_rate'] = stock['profit_loss_rate']
            all_news.extend(news_items)

    shuffle(all_news)
    all_news = all_news[:20]  # 전체 뉴스 20개로 제한

    # 섹터 데이터 처리
    sector_data = {}
    total_quantity = 0

    SECTOR_MAPPING = {
        'Healthcare': '헬스케어',
        'Technology': '기술',
        'Communication Services': '통신 서비스',
        'Energy': '에너지',
        'Consumer Cyclical': '경기소비재',
        'Consumer Defensive': '필수소비재',
        'Financial Services': '금융',
        'Financial': '금융',
        'Industrials': '산업재',
        'Basic Materials': '원자재',
        'Real Estate': '부동산',
        'Utilities': '유틸리티',
        'Consumer Discretionary': '임의소비재',
        'Information Technology': '정보기술',
        'Materials': '소재',
        'Telecommunications': '통신',
        'Consumer Staples': '생활필수품',
        'Health Care': '건강관리',
        'Commercial Services': '상업 서비스',
        'Capital Goods': '자본재',
        'Transportation': '운송',
        'Pharmaceuticals': '제약',
        'Biotechnology': '생명공학',
        'Software & Services': '소프트웨어 및 서비스',
        'Media & Entertainment': '미디어 및 엔터테인먼트',
        'Semiconductors': '반도체',
        'Retailing': '소매',
        'Food & Staples Retailing': '식품 및 생활용품 소매',
        'Food, Beverage & Tobacco': '식음료 및 담배',
        'Banks': '은행',
        'Insurance': '보험',
        'Diversified Financials': '다각화된 금융',
        'Automobiles & Components': '자동차 및 부품',
        'Other': '기타'
    }

    for stock in stock_holdings:
        korean_sector = SECTOR_MAPPING.get(stock['sector'], '기타')
        quantity = stock['amount']
        sector_data[korean_sector] = sector_data.get(korean_sector, 0) + quantity
        total_quantity += quantity

    sector_percentages = [
        {'sector': sector, 'percentage': (value / total_quantity * 100) if total_quantity > 0 else 0}
        for sector, value in sector_data.items()
    ]
    sector_percentages.sort(key=lambda x: x['percentage'], reverse=True)

    # 배당 캘린더 데이터 가져오기
    dividend_calendar = get_dividend_calendar(stock_holdings, tickers)

    context = {
        'acc_no': user_profile.acc_num,
        'stocks': stock_holdings,
        'total_value': balance['output3'].get('tot_asst_amt', 0),
        'total_stocks': len(stock_holdings),
        'PnL': float(balance['output3'].get('tot_evlu_pfls_amt')),
        'stock_news': all_news,
        'sector_percentages': sector_percentages,
        'dividend_calendar': dividend_calendar
    }

    # 결과 캐싱 (5분)
    cache.set(cache_key, context, 300)

    return render(request, 'portfolio/portfolio.html', context)


def get_company_logo(symbol):
    # 캐시 체크
    cache_key = f"company_logo_{symbol}"
    cached_logo = cache.get(cache_key)
    if cached_logo:
        return cached_logo

    # API 키가 필요없는 URL 목록
    logo_urls = [
        # f"https://d1u1p2xjjiahg3.cloudfront.net/logo/{symbol.upper()}.png",  # TradingView
        # f"https://cdn.icon-icons.com/icons2/2429/PNG/512/{symbol.lower()}_logo_icon_147274.png",  # Icon-Icons
        # f"https://cdn-icons-png.flaticon.com/512/{symbol.lower()}-logo.png",  # Flaticon
        f"https://companiesmarketcap.com/img/company-logos/64/{symbol.upper()}.png",  # Companies Market Cap
        # f"https://seeklogo.com/images/stock/{symbol.lower()}-logo.png",  # Seeklogo
        # f"https://s3.polygon.io/logos/{symbol.lower()}/logo.png",  # Polygon.io Public
        # f"https://eodhistoricaldata.com/img/logos/US/{symbol}.png"  # EOD Historical Data Public
    ]

    for url in logo_urls:
        try:
            response = requests.head(url, timeout=2)
            if response.status_code == 200:
                # 성공한 URL을 캐시에 저장 (24시간)
                cache.set(cache_key, url, 60 * 60 * 24)
                return url
        except:
            continue

    # 모든 시도가 실패하면 마지막 대안으로 Google Favicon 사용
    google_favicon = f"https://www.google.com/s2/favicons?domain={symbol.lower()}.com&sz=128"
    cache.set(cache_key, google_favicon, 60 * 60 * 24)
    return google_favicon


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

            balance = broker.fetch_balance_oversea()
            stock_holdings = []

            for comp in balance['output1']:
                stock_holdings.append({
                    'symbol': comp['ovrs_pdno'],
                    'profit_loss_rate': float(comp['evlu_pfls_rt'])
                })

            all_news = []
            with ThreadPoolExecutor(max_workers=5) as executor:
                news_futures = [executor.submit(fetch_stock_news, stock['symbol']) for stock in stock_holdings]
                for future, stock in zip(news_futures, stock_holdings):
                    news_items = future.result()
                    for news in news_items:
                        news['profit_loss_rate'] = stock['profit_loss_rate']
                    all_news.extend(news_items)

            shuffle(all_news)

            yield f"data: {json.dumps(all_news)}\n\n"
            time.sleep(60)  # 1분마다 업데이트

        except Exception as e:
            print(f"Error in generate_news: {str(e)}")
            yield f"data: {json.dumps([])}\n\n"

    response = StreamingHttpResponse(generate_news(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response
