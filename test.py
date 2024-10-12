import numpy as np
import pandas as pd
import yfinance as yf
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout


def get_stock_data(ticker, start_date, end_date):
    stock_data = yf.download(ticker, start=start_date, end=end_date)
    return stock_data


def prepare_data(data, look_back=60):
    scaler = MinMaxScaler(feature_range=(0, 1))
    scaled_data = scaler.fit_transform(data['Close'].values.reshape(-1, 1))

    X, y = [], []
    for i in range(look_back, len(scaled_data)):
        X.append(scaled_data[i - look_back:i, 0])
        y.append(scaled_data[i, 0])

    X, y = np.array(X), np.array(y)
    X = np.reshape(X, (X.shape[0], X.shape[1], 1))

    return X, y, scaler


def create_model(look_back):
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=(look_back, 1)))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50, return_sequences=True))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50))
    model.add(Dropout(0.2))
    model.add(Dense(units=1))
    model.compile(optimizer='adam', loss='mean_squared_error')
    return model


def train_model(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = create_model(X.shape[1])
    model.fit(X_train, y_train, epochs=100, batch_size=32, validation_data=(X_test, y_test), verbose=0)
    return model


def predict_next_day(model, data, scaler, look_back):
    last_60_days = data[-look_back:].values
    # Reshape last_60_days to a 2D array before scaling
    last_60_days = last_60_days.reshape(-1, 1)
    last_60_days_scaled = scaler.transform(last_60_days)
    X_test = np.reshape(last_60_days_scaled, (1, look_back, 1))
    pred_price = model.predict(X_test)
    pred_price = scaler.inverse_transform(pred_price)
    return pred_price[0][0]


def generate_signals(data, predictions):
    data['Predicted_Price'] = predictions
    data['Signal'] = 0
    data.loc[data['Predicted_Price'] > data['Close'], 'Signal'] = 1
    data.loc[data['Predicted_Price'] < data['Close'], 'Signal'] = -1
    return data


def backtest_strategy(data):
    data['Returns'] = data['Close'].pct_change()
    data['Strategy_Returns'] = data['Signal'].shift(1) * data['Returns']

    cumulative_returns = (1 + data['Strategy_Returns']).cumprod()
    total_return = cumulative_returns.iloc[-1] - 1

    return total_return


def main():
    ticker = "AAPL"
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    look_back = 60

    stock_data = get_stock_data(ticker, start_date, end_date)
    X, y, scaler = prepare_data(stock_data, look_back)
    model = train_model(X, y)

    predictions = []
    for i in range(look_back, len(stock_data)):
        pred = predict_next_day(model, stock_data['Close'][:i], scaler, look_back)
        predictions.append(pred)

    signals = generate_signals(stock_data[look_back:].copy(), predictions)
    total_return = backtest_strategy(signals)

    print(f"AI 기반 전략의 총 수익률: {total_return:.2%}")


if __name__ == "__main__":
    main()