# dashboard/views.py
import os

from django.shortcuts import render
from dotenv import load_dotenv

from .models import Stock
from django.utils import timezone
import mojito
import pprint
import requests
from bs4 import BeautifulSoup
import json
import os


def crawl_news():
    url = "https://www.investing.com/news/stock-market-news"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    news_list = soup.select('a[data-test="article-title-link"]')[:15]

    news_data = []
    for news in news_list:
        title = news.get_text(strip=True)
        link = news['href']
        if not link.startswith("https"):
            link = 'https://www.investing.com' + link
        news_data.append({
            'title': title,
            'link': link
        })
    return news_data


def crawl_article_content(article_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.121 Safari/537.36'
    }
    response = requests.get(article_url, headers=headers)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    article_body = soup.select_one('div.article_WYSIWYG__O0uhw')

    if article_body:
        return article_body.get_text(strip=True)
    else:
        return "No article content found."


def save_to_json(data, filename="news_data.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def articles(request):
    news_data = crawl_news()
    news_with_content = []

    for news in news_data:
        article_content = crawl_article_content(news['link'])
        news_with_content.append({
            'title': news['title'],
            'link': news['link'],
            'content': article_content
        })

    context = {
        'news': news_with_content,
    }

    return render(request, 'dashboard/articles.html', context)


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

    # 뉴스 데이터 가져오기
    news_data = crawl_news()
    news_with_content = []

    for news in news_data:
        article_content = crawl_article_content(news['link'])
        news_with_content.append({
            'title': news['title'],
            'link': news['link'],
            'content': article_content
        })

    context = {
        'acc_no': os.getenv('acc_no'),
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
        'news': news_with_content,  # 뉴스 데이터 추가
    }

    return render(request, 'dashboard/dashboard.html', context)
