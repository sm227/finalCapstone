from django.shortcuts import render
import requests
from datetime import datetime, timedelta
import pytz
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
from torch.autograd import Variable

# 한국 시간대 설정
korea_tz = pytz.timezone('Asia/Seoul')


# Alpha Vantage API로 시퀀스 데이터 가져오기
def get_actual_price(symbol):
    API_KEY = "U2UVDVWQ8ANZFDTW"
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min&apikey={API_KEY}"

    # Alpha Vantage API에서 데이터를 요청
    response = requests.get(url)
    data = response.json()

    if "Time Series (1min)" in data:
        # 타임스탬프가 최신 순서로 나열되므로, 가장 최신의 데이터를 가져옴
        latest_time = list(data["Time Series (1min)"].keys())[0]
        latest_data = data["Time Series (1min)"][latest_time]

        # 가장 최근의 종가를 추출
        actual_price = float(latest_data["4. close"])
        return actual_price
    else:
        # 데이터가 없을 경우, 실패 메시지 반환
        return None


# Alpha Vantage API로 시퀀스 데이터 가져오기
def get_sequence_data(symbol):
    API_KEY = "U2UVDVWQ8ANZFDTW"
    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=5min&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "Time Series (5min)" in data:
        sequence_data = []
        for time in data["Time Series (5min)"]:
            close_price = data["Time Series (5min)"][time]["4. close"]
            sequence_data.append(float(close_price))
        return sequence_data
    else:
        return None


# LSTM 모델 정의
class LSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, dropout=0.2):
        super(LSTM, self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        h_0 = Variable(torch.zeros(self.num_layers, x.size(0), self.hidden_size))
        c_0 = Variable(torch.zeros(self.num_layers, x.size(0), self.hidden_size))
        output, (hn, _) = self.lstm(x, (h_0, c_0))
        out = self.fc(hn[-1])
        return out


def predict_stock_price(request):
    if request.method == 'POST':
        symbol = request.POST.get('symbol')
        time_interval = int(request.POST.get('time_interval'))  # 5, 15, 30, 60 (분 단위)

        # 시퀀스 데이터 가져오기
        sequence_data = get_sequence_data(symbol)
        if sequence_data is None:
            return render(request, 'prediction/prediction_error.html', {'message': '실시간 주가 시퀀스를 가져오는 데 실패했습니다.'})

        # 실제 주가 가져오기
        actual_price = get_actual_price(symbol)
        if actual_price is None:
            return render(request, 'prediction/prediction_error.html', {'message': '실제 주가를 가져오는 데 실패했습니다.'})

        # 데이터 전처리
        scaler = MinMaxScaler()
        sequence_data = [[price] for price in sequence_data]

        if len(sequence_data) <= 30:
            return render(request, 'prediction/prediction_error.html', {'message': '데이터가 부족하여 예측을 할 수 없습니다. 더 많은 데이터가 필요합니다.'})

        scaled_data = scaler.fit_transform(sequence_data)

        # 시퀀스 설정 및 텐서 변환
        sequence_length = 30
        X_seq = [scaled_data[i:i + sequence_length] for i in range(len(scaled_data) - sequence_length)]
        if len(X_seq) == 0:
            return render(request, 'prediction/prediction_error.html', {'message': '시퀀스 데이터 생성에 실패했습니다.'})

        X_tensors = torch.Tensor(X_seq)

        # 모델 초기화
        input_size = 1
        hidden_size = 50
        num_layers = 2
        model = LSTM(input_size, hidden_size, num_layers)

        if len(X_tensors) > 0:
            future_X = X_tensors[-1].view(1, sequence_length, -1)

            # 예측
            with torch.no_grad():
                future_pred = model(future_X).detach().numpy()

            predicted_price = scaler.inverse_transform(future_pred)[0, 0]
        else:
            return render(request, 'prediction/prediction_error.html', {'message': '예측을 위한 유효한 데이터가 없습니다.'})

        # 현재 시간 계산
        end_time = datetime.now(korea_tz)
        prediction_time = end_time + timedelta(minutes=time_interval)

        context = {
            'symbol': symbol,
            'predicted_price': predicted_price,
            'prediction_time': prediction_time.strftime('%Y-%m-%d %H:%M'),
            'actual_price': actual_price,
        }

        return render(request, 'prediction/prediction_result.html', context)
    else:
        return render(request, 'prediction/prediction_form.html')
