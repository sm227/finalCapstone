from django.shortcuts import render

# articles/views.py

import requests
from bs4 import BeautifulSoup
import json
from django.shortcuts import render
import os
import google.generativeai as genai
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


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

    return render(request, 'articles/articles.html', context)


# 프롬프트 생성 함수
def generate_summary_prompt(article_title, article_content):
    """
    기사 내용을 요약하는 프롬프트를 생성하는 함수.
    :param article_title: 기사 제목
    :param article_content: 기사 내용
    :return: Gemini API에 보낼 프롬프트 텍스트
    """
    prompt = f"""
    The following is a news article titled "{article_title}":

    {article_content}

    이 글을 핵심 사항을 다루면서 요약하고 요약 내용을 글머리말로 표현해 주세요:
    - 짧고 명확한 문장을 사용합니다.
    - 가장 중요한 정보에 집중하세요.
    """
    return prompt


@csrf_exempt
def summarize_article(request):
    # 유해성 조정
    safety_settings = [
        {
            "category": "HARM_CATEGORY_DANGEROUS",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
    ]
    if request.method == 'POST':
        data = json.loads(request.body)
        article_title = data.get('title', '')  # 프론트에서 기사 제목을 받음
        article_content = data.get('content', '')  # 기사 내용 받음

        # Gemini API로 요약 요청 보내기
        try:

            # 본인 API 키 삽입 (세션 생성)

            genai.configure(api_key=os.getenv('gemini_api_key'))


            # 기사 요약 프롬프트 생성
            prompt = generate_summary_prompt(article_title, article_content)

            # 요약 요청
            model = genai.GenerativeModel("gemini-1.5-pro" ,safety_settings=safety_settings)

            response = model.generate_content(prompt)
            print('hello world')
            print(response.text)

            if response:
                # summary = response.generated_texts[0]  # 요약된 텍스트
                summary = response.text
                return JsonResponse({'summary': summary})
            else:
                return JsonResponse({'summary': '요약 실패'}, status=500)

        except Exception as e:
            return JsonResponse({'summary': 'error'}, status=500)