import os
import time
from django.shortcuts import render
from django.http import JsonResponse
import yfinance as yf
from datetime import datetime, timedelta
import pytz
import json
import pandas as pd
import numpy as np
import google.generativeai as genai

import module.koreainvestment as mojito
from login.models import UserProfile
from django.core.management import BaseCommand
from apscheduler.schedulers.background import BackgroundScheduler
from .models import StockRecommendation

# 파일 상단에 전역 변수 추가
ANALYSIS_IN_PROGRESS = False


def calculate_technical_indicators(df):
    # RSI 계산 (14일 기준)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD 계산
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # 볼린저 밴드 계산 (20일 기준)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['MA20'] + (std * 2)
    df['BB_Lower'] = df['MA20'] - (std * 2)

    return df


# 프롬프트 생성 함수
def generate_summary_prompt(data):
    """
    """
    prompt = f"""
    You are an expert in stock investing
    Your trading style is ultra-short term trading
    Your investing personality is aggressive
    You use a variety of indicators to make trading decisions
    
    stock data: "{data}"
    
    If you are a buyer, please provide a price target and stop loss
    Answer whether to buy or sell and why in JSON format
    example : 
    "action": "",
  "reason": "",
  "price_target": ,
  "stop_loss": 
    """
    return prompt


def stock_analysis(request):
    try:
        # URL 파라미터에서 티커 심볼 가져오기
        ticker_symbol = request.GET.get('symbol', 'AAPL')  # 기본값으로 AAPL 설정

        # 기존의 get_last_30min_data 함수 로직
        ticker = yf.Ticker(ticker_symbol)
        end_time = datetime.now(pytz.timezone('America/New_York'))
        start_time = end_time - timedelta(days=30)

        df = ticker.history(start=start_time, end=end_time, interval='1d')
        df = calculate_technical_indicators(df)

        json_data = {
            "symbol": ticker_symbol,
            "data": []
        }

        for index, row in df.tail(30).iterrows():  # 마지막 30분 데이터만 사용
            json_data["data"].append({
                "timestamp": index.strftime("%Y-%m-%d %H:%M:%S"),
                "price": {
                    "open": float(row['Open']),
                    "high": float(row['High']),
                    "low": float(row['Low']),
                    "close": float(row['Close']),
                    "volume": int(row['Volume'])
                },
                "indicators": {
                    "rsi": round(float(row['RSI']), 2) if not pd.isna(row['RSI']) else None,
                    "macd": {
                        "macd_line": round(float(row['MACD']), 2) if not pd.isna(row['MACD']) else None,
                        "signal_line": round(float(row['Signal_Line']), 2) if not pd.isna(row['Signal_Line']) else None
                    },
                    "bollinger_bands": {
                        "upper": round(float(row['BB_Upper']), 2) if not pd.isna(row['BB_Upper']) else None,
                        "middle": round(float(row['MA20']), 2) if not pd.isna(row['MA20']) else None,
                        "lower": round(float(row['BB_Lower']), 2) if not pd.isna(row['BB_Lower']) else None
                    }
                }
            })

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

        # Gemini API 처리
        genai.configure(api_key=os.getenv('gemini_api_key'))  # API 키는 환경변수로 관리하는 것을 추천
          # API 키는 환경변수로 관리하는 것을 추천
        prompt = generate_summary_prompt(json.dumps(json_data, indent=2, ensure_ascii=False))
        model = genai.GenerativeModel("gemini-1.5-pro", safety_settings=safety_settings)
        response = model.generate_content(prompt)

        # 최종 응답 데이터 구성
        result = {
            'stock_data': json_data,
            'analysis': response.text
        }

        # 응답 텍스트에서 JSON 부분만 추출
        response_text = response.text
        start_index = response_text.find('{')
        end_index = response_text.rfind('}') + 1
        json_str = response_text[start_index:end_index]

        # JSON 문자열을 파이썬 딕셔너리로 파싱
        response_data = json.loads(json_str)
        print(response.text)
        print(response_data['action'])

        if response_data['action'].lower() == 'buy':
            # 현재 로그인한 사용자의 UserProfile 가져오기
            try:
                user_profile = UserProfile.objects.get(user=request.user)
                buy(ticker_symbol, user_profile)
            except UserProfile.DoesNotExist:
                # UserProfile이 없는 경우 에러 처리
                return JsonResponse({'message': '사용자 프로필을 찾을 수 없습니다.'}, status=400)

        return JsonResponse(response.text, safe=False)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def index(request):
    recommendations = StockRecommendation.objects.all().order_by('-created_at')
    
    # 분석 중이거나 데이터가 없는 경우 로딩 페이지 표시
    if ANALYSIS_IN_PROGRESS or not recommendations.exists():
        return render(request, 'analytics2/loading.html', {
            'is_analyzing': ANALYSIS_IN_PROGRESS
        })
    
    return render(request, 'analytics2/index.html', {'recommendations': recommendations})


def buy(ticker_symbol, user_profile):
    # 한국투자 API 연결
    broker = mojito.KoreaInvestment(
        api_key=user_profile.api_key,
        api_secret=user_profile.api_secret,
        acc_no=user_profile.acc_num,  # 계좌 번호
        exchange='나스닥',  # 애플 주식을 구매할 때 사용 (NASDAQ)
        mock=True  # 모의 투자 모드
    )

    # 주문 실행
    broker.create_oversea_order(
        side='buy',  # 매수
        symbol=ticker_symbol,  # 주식 코드
        price=1000,  # 지정가
        quantity=5,  # 수
        order_type="00"  # 00은 지정가 주문
    )


def sell(predict_price, user_profile):
    # 한국투자 API 연결
    broker = mojito.KoreaInvestment(
        api_key=user_profile.api_key,
        api_secret=user_profile.api_secret,
        acc_no=user_profile.acc_num,  # 계좌 번호
        exchange='나스닥',  # 애플 주식을 구매할 때 사용 (NASDAQ)
        mock=True  # 모의 투자 모드
    )

    # 주문 실행
    broker.create_oversea_order(
        side='sell',  # 매도
        symbol='AAPL',  # 주식 코드
        price=predict_price,  # 지정가
        quantity=5,  # 수량
        order_type="00"  # 00은 지정가 주문
    )


def read_aggressive_stocks():
    with open('공격형.txt', 'r') as file:
        stocks = file.readlines()
    return [stock.strip() for stock in stocks][:5]  # 상위 5개만 반환

def analyze_and_store_stocks():
    global ANALYSIS_IN_PROGRESS
    try:
        # 이미 분석 중이면 실행하지 않음
        if ANALYSIS_IN_PROGRESS:
            print("이미 분석이 진행 중입니다.")
            return
            
        ANALYSIS_IN_PROGRESS = True
        stocks = read_aggressive_stocks()
        
        for ticker_symbol in stocks:
            # 기존 추천이 있는지 확인
            if StockRecommendation.objects.filter(symbol=ticker_symbol).exists():
                print(f"{ticker_symbol}은 이미 분석되어 있습니다.")
                continue
                
            print(f"{ticker_symbol} 분석 시작")
            # 기존 분석 로직
            ticker = yf.Ticker(ticker_symbol)
            end_time = datetime.now(pytz.timezone('America/New_York'))
            start_time = end_time - timedelta(days=30)
            
            df = ticker.history(start=start_time, end=end_time, interval='1d')
            df = calculate_technical_indicators(df)
            
            # JSON 데이터 구성 (기존 코드와 동일)
            json_data = {
                "symbol": ticker_symbol,
                "data": []
            }
           
           
            for index, row in df.tail(30).iterrows():  # 마지막 30분 데이터만 사용
                json_data["data"].append({
                    "timestamp": index.strftime("%Y-%m-%d %H:%M:%S"),
                    "price": {
                        "open": float(row['Open']),
                        "high": float(row['High']),
                        "low": float(row['Low']),
                        "close": float(row['Close']),
                        "volume": int(row['Volume'])
                    },
                    "indicators": {
                        "rsi": round(float(row['RSI']), 2) if not pd.isna(row['RSI']) else None,
                        "macd": {
                            "macd_line": round(float(row['MACD']), 2) if not pd.isna(row['MACD']) else None,
                            "signal_line": round(float(row['Signal_Line']), 2) if not pd.isna(row['Signal_Line']) else None
                        },
                        "bollinger_bands": {
                            "upper": round(float(row['BB_Upper']), 2) if not pd.isna(row['BB_Upper']) else None,
                            "middle": round(float(row['MA20']), 2) if not pd.isna(row['MA20']) else None,
                            "lower": round(float(row['BB_Lower']), 2) if not pd.isna(row['BB_Lower']) else None
                        }
                    }
                })


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

            # Gemini API 분석
            genai.configure(api_key=os.getenv('gemini_api_key'))  # API 키는 환경변수로 관리하는 것을 추천
            prompt = generate_summary_prompt(json.dumps(json_data, indent=2, ensure_ascii=False))
            model = genai.GenerativeModel("gemini-1.5-pro", safety_settings=safety_settings)
            response = model.generate_content(prompt)
            
            # JSON 응답 파싱
            response_text = response.text
            start_index = response_text.find('{')
            end_index = response_text.rfind('}') + 1
            json_str = response_text[start_index:end_index]
            response_data = json.loads(json_str)
            
            # 한 번만 출력
            action = response_data['action'].lower()
            print(f"{ticker_symbol} 분석 결과: {action}")
            
            # 매수 추천인 경우 DB에 저장
            if action == 'buy':
                StockRecommendation.objects.create(
                    symbol=ticker_symbol,
                    action=response_data['action'],
                    reason=response_data['reason'],
                    price_target=response_data['price_target'],
                    stop_loss=response_data['stop_loss']
                )
            time.sleep(60)  # API 호출 제한 고려
                
    except Exception as e:
        print(f"Error during analysis: {str(e)}")
    finally:
        ANALYSIS_IN_PROGRESS = False

def start_scheduler():
    scheduler = BackgroundScheduler()
    # 즉시 첫 분석 실행
    analyze_and_store_stocks()
    # 이후 하루마다 실행
    scheduler.add_job(analyze_and_store_stocks, 'interval', days=1)
    scheduler.start()
