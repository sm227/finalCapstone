from django.shortcuts import render, redirect
import module.koreainvestment as mojito
from django.http import JsonResponse
from login.models import UserProfile
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from dotenv import load_dotenv
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.contrib.auth.decorators import login_required

load_dotenv()


@login_required(login_url='login')
def trading(request):
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
        acc_no=user_profile.acc_num,  # 계좌 번호
        exchange='나스닥',
        mock=True
    )

    balance = broker.fetch_present_balance()
    test = broker.fetch_balance_oversea()
    print(balance)
    print("test: ", test)
    stock_holdings = []
    total_value = 0

    # for comp in balance['output1']:
    #     stock_holdings.append({
    #         'symbol': comp['pdno'],
    #         'name': comp['prdt_name'],
    #         'country': comp['natn_kor_name'],
    #         'exchange_code': comp['ovrs_excg_cd'],
    #         'market_name': comp['tr_mket_name'],
    #         'profit_loss_rate': float(comp['evlu_pfls_rt1']),
    #         'exchange_rate': float(comp['bass_exrt']),
    #         'purchase_amount_foreign': float(comp['frcr_pchs_amt']),
    #         'last_updated': timezone.now(),
    #     })

    for comp in test['output1']:
        stock_holdings.append({
            'symbol': comp['ovrs_pdno'],
            'name': comp['ovrs_item_name'],
            'amount' : comp['ovrs_cblc_qty'],
            'exchange_code': comp['ovrs_excg_cd'],
            'profit_loss_rate': float(comp['evlu_pfls_rt']),
            'last_updated': timezone.now(),
        })

    total_value = balance['output3'].get('tot_asst_amt', 0)
    PnL = balance['output3'].get('tot_evlu_pfls_amt')

    context = {
        'acc_no': user_profile.acc_num,
        'stocks': stock_holdings,
        'total_value': total_value,
        'total_stocks': len(stock_holdings),
        'PnL': float(PnL)
    }

    return render(request, 'trading/trading.html', context)


@csrf_exempt  # CSRF 비활성화 (테스트 용도)
def place_order(request):
    # 현재 로그인한 사용자의 UserProfile 가져오기
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # UserProfile이 없는 경우 에러 처리
        return JsonResponse({'message': '사용자 프로필을 찾을 수 없습니다.'}, status=400)

    # 한국투자 API 연결
    broker = mojito.KoreaInvestment(
        api_key=user_profile.api_key,
        api_secret=user_profile.api_secret,
        acc_no=user_profile.acc_num,  # 계좌 번호
        exchange='나스닥',  # 애플 주식을 구매할 때 사용 (NASDAQ)
        mock=True  # 모의 투자 모드
    )
    if request.method == "POST":
        try:
            # JSON 요청 데이터를 파싱
            data = json.loads(request.body)
            stock_code = data.get('stock_code')
            price = float(data.get('price'))
            quantity = int(data.get('quantity', 1))  # 기본 수량은 1로 설정

            if price is None or quantity is None or stock_code is None:
                return JsonResponse({'message': '필수 매개변수가 누락되었습니다.'}, status=400)

            # 주문 실행
            response = broker.create_oversea_order(
                side='buy',  # 매수
                symbol=stock_code,  # 주식 코드
                price=price,  # 지정가
                quantity=quantity,  # 수량
                order_type="00"  # 00은 지정가 주문
            )

            print(response)
            # 주문 응답 처리
            if response.get('rt_cd') == '0' and '모의투자 매수주문이 완료 되었습니다.' in response.get('msg1', ''):
                return JsonResponse({'message': 'complete'})
            elif '모의투자 장시작전 입니다.' in response.get('msg1', ''):
                return JsonResponse({'message': 'market_not_open'}, status=400)
            elif '모의투자 주문처리가 안되었습니다(매매불가 종목)' in response.get('msg1', ''):
                return JsonResponse({'message': 'stockcode_not_exist'}, status=400)
            elif '모의투자 장종료 입니다.' in response.get('msg1', ''):
                return JsonResponse({'message': 'market_closed'}, status=400)
            else:
                err_message = response.get('msg1', 'Unknown error')
                return JsonResponse({'message': f'failed: {err_message}'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error occurred: {e}")
            return JsonResponse({'message': f'error: {str(e)}'}, status=400)

        return JsonResponse({'message': 'Invalid request method'}, status=405)


@csrf_exempt
def place_order_sell(request):
    # print("호출")
    # 현재 로그인한 사용자의 UserProfile 가져오기
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # UserProfile이 없는 경우 에러 처리
        return JsonResponse({'message': '사용자 프로필을 찾을 수 없습니다.'}, status=400)

    # 한국투자 API 연결
    broker = mojito.KoreaInvestment(
        api_key=user_profile.api_key,
        api_secret=user_profile.api_secret,
        acc_no=user_profile.acc_num,  # 계좌 번호
        exchange='나스닥',  # 애플 주식을 구매할 때 사용 (NASDAQ)
        mock=True  # 모의 투자 모드
    )

    if request.method == 'POST':
        try:
            print("매도")
            data = json.loads(request.body)
            # print(data)

            stock_code = data.get('stock_code')
            price = float(data.get('price'))
            quantity = int(data.get('quantity', 1))

            if price is None or quantity is None or stock_code is None:
                return JsonResponse({'message': '필수 매개변수가 누락되었습니다.'}, status=400)

            response = broker.create_oversea_order(
                side='sell',
                symbol=stock_code,
                price=price,
                quantity=quantity,
                order_type="00"
            )
            print(response)
            if response.get('rt_cd') == '0' and '모의투자 매도주문이 완료 되었습니다.' in response.get('msg1', ''):
                return JsonResponse({'message': 'complete'})
            elif '모의투자 장시작전 입니다.' in response.get('msg1', ''):
                return JsonResponse({'message': 'market_not_open'}, status=400)
            elif '모의투자 주문처리가 안되었습니다(매매불가 종목)' in response.get('msg1', ''):
                return JsonResponse({'message': 'stockcode_not_exist'}, status=400)
            elif '모의투자 장종료 입니다.' in response.get('msg1', ''):
                return JsonResponse({'message': 'market_closed'}, status=400)
            elif '모의투자 잔고내역이 없습니다' in response.get('msg1', ''):
                return JsonResponse({'message': 'does_not_have'}, status=400)
            else:
                err_message = response.get('msg1', 'Unknown error')
                return JsonResponse({'message': f'failed: {err_message}'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error occurred: {e}")
            return JsonResponse({'message': f'error: {str(e)}'}, status=400)

    return JsonResponse({'message': 'Invalid request method'}, status=405)


def get_stock_data(request):
    load_dotenv()

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        # UserProfile이 없는 경우 에러 처리
        return JsonResponse({'message': '사용자 프로필을 찾을 수 없습니다.'}, status=400)

    # 한국투자 API 연결
    broker = mojito.KoreaInvestment(
        api_key=user_profile.api_key,
        api_secret=user_profile.api_secret,
        acc_no=user_profile.acc_num,  # 계좌 번호
        exchange='나스닥',  # 애플 주식을 구매할 때 사용 (NASDAQ)
        mock=True  # 모의 투자 모드
    )

    balance = broker.fetch_present_balance()
    test = broker.fetch_balance_oversea()
    #print(balance)
    stock_holdings = []

    for comp in test['output1']:
        stock_holdings.append({
            'symbol': comp['ovrs_pdno'],
            'name': comp['ovrs_item_name'],
            'amount': comp['ovrs_cblc_qty'],
            'exchange_code': comp['ovrs_excg_cd'],
            'profit_loss_rate': float(comp['evlu_pfls_rt']),
            'last_updated': timezone.now(),
        })

    total_value = balance['output3'].get('tot_asst_amt', 0)
    PnL = balance['output3'].get('tot_evlu_pfls_amt')

    return JsonResponse({
        'PnL': float(PnL),
        'stocks': stock_holdings,
    })
