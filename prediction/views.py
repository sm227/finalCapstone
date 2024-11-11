# prediction/views.py
import torch
import torch.nn as nn
from torch.autograd import Variable
import yfinance as yf
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from datetime import datetime, timedelta
import pytz
from django.shortcuts import render
from django.http import JsonResponse

# 한국 시간대 설정
korea_tz = pytz.timezone('Asia/Seoul')


# LSTM 모델 정의
class LSTM(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, dropout=0.2):
        super(LSTM, self).__init__()
        self.hidden_size = hidden_size  # hidden_size를 인스턴스 변수로 저장
        self.num_layers = num_layers  # num_layers를 인스턴스 변수로 저장
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        h_0 = Variable(torch.zeros(self.num_layers, x.size(0), self.hidden_size))  # self.num_layers, self.hidden_size 사용
        c_0 = Variable(torch.zeros(self.num_layers, x.size(0), self.hidden_size))  # self.num_layers, self.hidden_size 사용
        output, (hn, _) = self.lstm(x, (h_0, c_0))
        out = self.fc(hn[-1])
        return out


def predict_stock_price(request):
    if request.method == 'POST':
        # 사용자 입력 받기
        symbol = request.POST.get('symbol')
        time_interval = request.POST.get('time_interval')  # 5min, 15min, 30min, 1hour
        prediction_date = request.POST.get('prediction_date')
        prediction_time = request.POST.get('prediction_time')

        # 예측을 위한 시간 조합
        end_time_str = f"{prediction_date} {prediction_time}"
        end_time = korea_tz.localize(datetime.strptime(end_time_str, '%Y-%m-%d %H:%M'))

        # 데이터 가져오기 (3일치 5분 간격 데이터)
        start_time = end_time - timedelta(days=3)
        df = yf.download(symbol, start=start_time.strftime('%Y-%m-%d'), end=end_time.strftime('%Y-%m-%d'),
                         interval="5m")

        # 데이터 전처리
        if not df.empty:
            X = df.drop('Close', axis=1)
            y = df[['Close']]
            ss = StandardScaler()
            ms = MinMaxScaler()
            X_ss = ss.fit_transform(X)
            y_ms = ms.fit_transform(y)

            # 시퀀스 길이 설정 및 데이터 시퀀스화
            sequence_length = 30
            X_seq, y_seq = [], []
            for i in range(len(X_ss) - sequence_length):
                X_seq.append(X_ss[i:i + sequence_length])
                y_seq.append(y_ms[i + sequence_length])

            X_tensors = torch.Tensor(X_seq)
            y_tensors = torch.Tensor(y_seq)

            # 모델 초기화 및 학습
            input_size = X.shape[1]
            hidden_size = 50
            num_layers = 2
            model = LSTM(input_size, hidden_size, num_layers)
            criterion = nn.MSELoss()
            optimizer = torch.optim.Adam(model.parameters(), lr=0.0001)

            # 학습
            num_epochs = 300
            for epoch in range(num_epochs):
                outputs = model(X_tensors)
                optimizer.zero_grad()
                loss = criterion(outputs, y_tensors)
                loss.backward()
                optimizer.step()

            # 예측 시간 설정
            future_X = X_tensors[-1].view(1, sequence_length, -1)

            # 예측
            with torch.no_grad():
                future_pred = model(future_X).detach().numpy()

            # 예측값을 원래 스케일로 변환
            predicted_price = ms.inverse_transform(future_pred)[0, 0]

            # 예측된 가격 출력
            prediction_time = end_time + timedelta(minutes=int(time_interval))  # 예측 시간
            actual_price_time = prediction_time.astimezone(pytz.utc)

            try:
                if actual_price_time not in df.index:
                    closest_time_idx = (df.index.to_series() - actual_price_time).abs().idxmin()
                    closest_time = df.index[closest_time_idx]
                    actual_price = df.loc[closest_time]['Close'].item()
                else:
                    actual_price = df.loc[actual_price_time]['Close'].item()

                accuracy = 100 - abs(predicted_price - actual_price) / actual_price * 100
            except Exception as e:
                accuracy = None

            context = {
                'symbol': symbol,
                'predicted_price': predicted_price,
                'actual_price': actual_price if accuracy else None,
                'accuracy': accuracy if accuracy else None,
                'prediction_time': prediction_time.strftime('%Y-%m-%d %H:%M')
            }

            return render(request, 'prediction/prediction_result.html', context)
        else:
            return render(request, 'prediction/prediction_error.html', {'message': '데이터를 가져올 수 없습니다.'})

    return render(request, 'prediction/prediction_form.html')