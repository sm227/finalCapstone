import numpy as np
import pandas as pd
import yfinance as yf
import time
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import EarlyStopping
import ta  # 기술적 지표를 위한 라이브러리

class EnhancedStockPredictor:
    def __init__(self, symbol, prediction_minutes=5):
        self.symbol = symbol
        self.prediction_minutes = prediction_minutes
        self.model = None
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        
    def get_technical_indicators(self, data):
        # RSI 추가
        data['RSI'] = ta.momentum.RSIIndicator(data['Close']).rsi()
        
        # MACD 추가
        macd = ta.trend.MACD(data['Close'])
        data['MACD'] = macd.macd()
        data['MACD_signal'] = macd.macd_signal()
        
        # 볼린저 밴드 추가
        bollinger = ta.volatility.BollingerBands(data['Close'])
        data['BB_high'] = bollinger.bollinger_hband()
        data['BB_low'] = bollinger.bollinger_lband()
        
        # 이동평균선 추가
        data['MA5'] = ta.trend.sma_indicator(data['Close'], window=5)
        data['MA20'] = ta.trend.sma_indicator(data['Close'], window=20)
        
        # 거래량 지표 추가
        data['Volume_MA5'] = ta.trend.sma_indicator(data['Volume'], window=5)
        data['Volume_MA20'] = ta.trend.sma_indicator(data['Volume'], window=20)
        
        return data
    
    def get_realtime_data(self):
        stock = yf.Ticker(self.symbol)
        # 더 많은 과거 데이터를 가져와서 학습
        data = stock.history(period='5d', interval='1m')
        return self.get_technical_indicators(data)
    
    def prepare_data(self, data):
        # 결측치 처리
        data = data.fillna(method='ffill')
        
        features = ['Open', 'High', 'Low', 'Close', 'Volume',
                   'RSI', 'MACD', 'MACD_signal', 
                   'BB_high', 'BB_low', 
                   'MA5', 'MA20',
                   'Volume_MA5', 'Volume_MA20']
        
        dataset = data[features].values
        scaled_data = self.scaler.fit_transform(dataset)
        
        X, y = [], []
        sequence_length = 120  # 시퀀스 길이 증가
        
        for i in range(sequence_length, len(scaled_data) - self.prediction_minutes):
            X.append(scaled_data[i-sequence_length:i])
            y.append(scaled_data[i + self.prediction_minutes, 3])  # Close 가격 예측
            
        return np.array(X), np.array(y)
    
    def build_model(self, input_shape):
        model = Sequential([
            LSTM(units=128, return_sequences=True, input_shape=input_shape),
            BatchNormalization(),
            Dropout(0.3),
            
            LSTM(units=128, return_sequences=True),
            BatchNormalization(),
            Dropout(0.3),
            
            LSTM(units=64, return_sequences=False),
            BatchNormalization(),
            Dropout(0.3),
            
            Dense(units=32, activation='relu'),
            BatchNormalization(),
            Dropout(0.2),
            
            Dense(units=1)
        ])
        
        optimizer = Adam(learning_rate=0.001)
        model.compile(optimizer=optimizer, loss='huber')  # Huber loss 사용
        return model
    
    def train(self):
        data = self.get_realtime_data()
        X, y = self.prepare_data(data)
        
        # 조기 종료 콜백 추가
        early_stopping = EarlyStopping(
            monitor='val_loss',
            patience=10,
            restore_best_weights=True
        )
        
        self.model = self.build_model(input_shape=(X.shape[1], X.shape[2]))
        
        # 검증 세트 분리
        split = int(len(X) * 0.8)
        X_train, X_val = X[:split], X[split:]
        y_train, y_val = y[:split], y[split:]
        
        self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=100,
            batch_size=32,
            callbacks=[early_stopping],
            verbose=1
        )
    
    def predict_next(self):
        data = self.get_realtime_data()
        features = ['Open', 'High', 'Low', 'Close', 'Volume',
                   'RSI', 'MACD', 'MACD_signal', 
                   'BB_high', 'BB_low', 
                   'MA5', 'MA20',
                   'Volume_MA5', 'Volume_MA20']
        
        recent_data = data[features].tail(120).values
        scaled_data = self.scaler.transform(recent_data)
        X = scaled_data.reshape(1, 120, len(features))
        
        predicted_scaled = self.model.predict(X)
        
        dummy_array = np.zeros((1, len(features)))
        dummy_array[0, 3] = predicted_scaled[0, 0]
        predicted_price = self.scaler.inverse_transform(dummy_array)[0, 3]
        
        current_price = data['Close'].iloc[-1]
        predicted_change = ((predicted_price - current_price) / current_price) * 100
        
        # 매매 신호 생성 로직에 가격 정보 추가
        signal = self.generate_trading_signal(data, predicted_change, current_price, predicted_price)
        
        return predicted_price, predicted_change, signal
    
    def generate_trading_signal(self, data, predicted_change, current_price, predicted_price):
        rsi = data['RSI'].iloc[-1]
        macd = data['MACD'].iloc[-1]
        macd_signal = data['MACD_signal'].iloc[-1]
        
        signal = {
            'type': 'NEUTRAL',
            'strength': 0,
            'reasons': [],
            'current_price': round(current_price, 2),
            'predicted_price': round(predicted_price, 2),
            'prediction_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # 강한 매수 신호
        if (predicted_change > 1.5 and
            rsi < 70 and
            macd > macd_signal):
            signal['type'] = 'STRONG_BUY'
            signal['strength'] = 2
            signal['reasons'].append(f'현재가격: ${current_price:.2f}')
            signal['reasons'].append(f'예측가격: ${predicted_price:.2f} (+{predicted_change:.1f}%)')
            signal['reasons'].append('MACD 골든크로스')
        
        # 매수 신호
        elif (predicted_change > 0.5 and
              rsi < 65):
            signal['type'] = 'BUY'
            signal['strength'] = 1
            signal['reasons'].append(f'현재가격: ${current_price:.2f}')
            signal['reasons'].append(f'예측가격: ${predicted_price:.2f} (+{predicted_change:.1f}%)')
        
        # 매도 신호
        elif (predicted_change < -0.5 and
              rsi > 35):
            signal['type'] = 'SELL'
            signal['strength'] = -1
            signal['reasons'].append(f'현재가격: ${current_price:.2f}')
            signal['reasons'].append(f'예측가격: ${predicted_price:.2f} ({predicted_change:.1f}%)')
        
        # 강한 매도 신호
        elif (predicted_change < -1.5 and
              rsi > 30 and
              macd < macd_signal):
            signal['type'] = 'STRONG_SELL'
            signal['strength'] = -2
            signal['reasons'].append(f'현재가격: ${current_price:.2f}')
            signal['reasons'].append(f'예측가격: ${predicted_price:.2f} ({predicted_change:.1f}%)')
            signal['reasons'].append('MACD 데드크로스')
        
        # 중립 신호일 경우에도 가격 정보 포함
        else:
            signal['reasons'].append(f'현재가격: ${current_price:.2f}')
            signal['reasons'].append(f'예측가격: ${predicted_price:.2f} ({predicted_change:.1f}%)')
        
        return signal

# 사용 예시
if __name__ == "__main__":
    predictor = EnhancedStockPredictor("AAPL", prediction_minutes=5)
    predictor.train()
    
    while True:
        predicted_price, predicted_change, signal = predictor.predict_next()
        print(f"현재 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"예측된 {predictor.prediction_minutes}분 후 가격: ${predicted_price:.2f}")
        print(f"예상 변동률: {predicted_change:.2f}%")
        print(f"매매 신호: {signal['type']} ({signal['strength']})")
        print("-" * 50)
        time.sleep(60)
