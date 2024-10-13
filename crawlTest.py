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


news_data = crawl_news()

news_with_content = []

for idx, news in enumerate(news_data, 1):
    article_content = crawl_article_content(news['link'])
    news_with_content.append({
        'title': news['title'],
        'link': news['link'],
        'content': article_content
    })

save_to_json(news_with_content)

print("News articles saved to 'news_data.json'")
