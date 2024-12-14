import os
import time
from urllib import request

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
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from dotenv import load_dotenv
from pytz import timezone

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
        load_dotenv()

        # Gemini API 처리
        genai.configure(api_key=os.getenv('gemini_api_key'))  # API 키는 환경변수로 관리하는 것을 추천
          # API 키는 환경변수로 관리하는 것을 추천
        prompt = generate_summary_prompt(json.dumps(json_data, indent=2, ensure_ascii=False))
        model = genai.GenerativeModel("gemini-1.5-flash", safety_settings=safety_settings)
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


@login_required(login_url='login')
def index(request):
    recommendations = StockRecommendation.objects.all().order_by('-created_at')

    # 현재 사용자의 투자 성향 가져오기
    investment_style = None
    if request.user.is_authenticated:
        try:
            investment_style = request.user.userprofile.investment_style
        except:
            pass

    # 각 추천 종목의 수익률 계산
    for rec in recommendations:
        try:
            # yfinance로 주식 데이터 가져오기
            ticker = yf.Ticker(rec.symbol)

            # 추천일의 종가 가져오기
            rec_date = rec.created_at.strftime('%Y-%m-%d')
            hist = ticker.history(start=rec_date, end=(rec.created_at + timedelta(days=1)).strftime('%Y-%m-%d'))
            if not hist.empty:
                rec_close = hist['Close'].iloc[0]

                # 현재가 가져오기
                current_price = ticker.history(period='1d')['Close'].iloc[-1]

                # 수익률 계산
                profit_rate = ((current_price - rec_close) / rec_close) * 100
                rec.profit_rate = round(profit_rate, 2)
                rec.current_price = round(current_price, 2)
                rec.rec_close = round(rec_close, 2)
            else:
                rec.profit_rate = None
                rec.current_price = None
                rec.rec_close = None
        except Exception as e:
            print(f"Error calculating profit rate for {rec.symbol}: {str(e)}")
            rec.profit_rate = None
            rec.current_price = None
            rec.rec_close = None

    return render(request, 'analytics2/index.html', {
        'recommendations': recommendations,
        'investment_style': investment_style
    })


def buy(ticker_symbol, user_profile):
    # 현재 주식 가격 조회
    ticker = yf.Ticker(ticker_symbol)
    current_price = ticker.history(period='1d')['Close'].iloc[-1]

    # 주문 수량 계산
    if user_profile.per_stock_amount:
        quantity = int(float(user_profile.per_stock_amount) / current_price)
    else:
        # 기본값으로 1주 설정
        quantity = 1

    # 최소 1주 이상 확인
    quantity = max(1, quantity)

    # 총 투자금액 제한 확인
    if user_profile.total_investment:
        max_quantity = int(float(user_profile.total_investment) / current_price)
        quantity = min(quantity, max_quantity)

    # 한국투자 API 연결
    broker = mojito.KoreaInvestment(
        api_key=user_profile.api_key,
        api_secret=user_profile.api_secret,
        acc_no=user_profile.acc_num,
        exchange='나스닥',
        mock=True
    )

    # 주문 실행
    broker.create_oversea_order(
        side='buy',
        symbol=ticker_symbol,
        price=current_price,  # 현재가로 설정
        quantity=quantity,
        order_type="00"  # 지정가 주문
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


def read_stocks_by_style(investment_style):
    # 투자 성향에 따른 파일명 매핑
    style_files = {
        'conservative': '안정형.txt',
        'balanced': '중립형.txt',
        'aggressive': '공격형.txt'
    }

    # 해당하는 투자 성향의 파일 읽기
    file_name = style_files.get(investment_style, '중립형.txt')  # 기본값으로 중립형 설정
    try:
        with open(file_name, 'r', encoding='utf-8') as file:
            stocks = file.readlines()
        return [stock.strip() for stock in stocks]
    except FileNotFoundError:
        print(f"파일을 찾을 수 없습니다: {file_name}")
        return []

def analyze_and_store_stocks():
    global ANALYSIS_IN_PROGRESS
    try:
        if ANALYSIS_IN_PROGRESS:
            print("이미 분석이 진행 중입니다.")
            return

        ANALYSIS_IN_PROGRESS = True

        # 각 투자 성향별로 분석 수행
        for style, _ in UserProfile.INVESTMENT_CHOICES:
            stocks = read_stocks_by_style(style)
            if not stocks:
                continue

            # 해당 투자 성향을 가진 사용자들 필터링
            users_with_style = UserProfile.objects.filter(investment_style=style)
            if not users_with_style.exists():
                continue

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
                load_dotenv()

                # Gemini API 분석
                genai.configure(api_key=os.getenv('gemini_api_key'))  # API 키는 환경변수로 관리하는 것을 추천
                prompt = generate_summary_prompt(json.dumps(json_data, indent=2, ensure_ascii=False))
                model = genai.GenerativeModel("gemini-1.5-flash", safety_settings=safety_settings)
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

                    # 자동투자가 활성화된 모든 사용자에 대해 매수 실행
                    auto_invest_users = UserProfile.objects.filter(auto_investment=True)
                    for user_profile in auto_invest_users:
                        try:
                            buy(ticker_symbol, user_profile)
                        except Exception as e:
                            print(f"Error buying for user {user_profile.user.username}: {str(e)}")


                time.sleep(60)  # API 호출 제한 고려

    except Exception as e:
        print(f"Error during analysis: {str(e)}")
    finally:
        ANALYSIS_IN_PROGRESS = False

def start_scheduler():
    scheduler = BackgroundScheduler()
    # 매일 밤 11시 40분에 ��행되도록 설정, 시간대 명시
    scheduler.add_job(analyze_and_store_stocks, 'cron', hour=23, minute=40, timezone=timezone('Asia/Seoul'))
    scheduler.start()

@login_required
@require_POST
def update_investment_style(request):
    try:
        style = request.POST.get('style')
        if style not in ['conservative', 'balanced', 'aggressive']:
            return JsonResponse({'error': '잘못된 투자 성향입니다.'}, status=400)

        profile = request.user.userprofile
        profile.investment_style = style
        profile.save()

        return JsonResponse({'message': '투자 성향이 업데이트되었습니다.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_POST
def update_auto_investment(request):
    try:
        # JSON 데이터 파싱
        data = json.loads(request.body)
        enabled = data.get('enabled', False)
        print(enabled)

        # UserProfile 업데이트
        profile = request.user.userprofile
        profile.auto_investment = enabled
        profile.save()

        return JsonResponse({
            'success': True,
            'message': '자동투자 설정이 업데이트되었습니다.',
            'enabled': enabled
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

@login_required
@require_POST
def update_portfolio_settings(request):
    try:
        # JSON 데이터 파싱
        data = json.loads(request.body)
        total_investment = data.get('total_investment')
        per_stock_amount = data.get('per_stock_amount')

        # 입력값 검증
        if not total_investment or not per_stock_amount:
            return JsonResponse({'error': '모든 필드를 입력해주세요.'}, status=400)

        try:
            total_investment = float(total_investment)
            per_stock_amount = float(per_stock_amount)
        except ValueError:
            return JsonResponse({'error': '유효한 숫자를 입력해주세요.'}, status=400)

        if total_investment < 0 or per_stock_amount < 0:
            return JsonResponse({'error': '금액은 0보다 커야 합니다.'}, status=400)

        if per_stock_amount > total_investment:
            return JsonResponse({'error': '종목당 투자금액은 총 투자금액을 초과할 수 없습니다.'}, status=400)

        # UserProfile 업데이트
        profile = request.user.userprofile
        profile.total_investment = total_investment
        profile.per_stock_amount = per_stock_amount
        profile.save()

        return JsonResponse({
            'success': True,
            'message': '포트폴리오 설정이 업데이트되었습니다.'
        })
    except Exception as e:
        return JsonResponse({'error':  str(e)}, status=500)
