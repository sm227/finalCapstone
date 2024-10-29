# stock_prediction/forms.py
from django import forms


class StockPredictionForm(forms.Form):
    TIME_CHOICES = [
        ('days', 'Days'),
        ('hours', 'Hours'),
        ('minutes', 'Minutes'),
    ]

    MODEL_CHOICES = [
        ('RandomForestRegressor', 'Random Forest'),
        ('ExtraTreesRegressor', 'Extra Trees'),
        ('XGBRegressor', 'XGBoost'),
        ('LinearRegression', 'Linear Regression'),
        ('KNeighborsRegressor', 'K-Neighbors'),
        ('LSTM', 'LSTM Neural Network'),
    ]

    company = forms.CharField(
        max_length=10,
        initial='GOOG',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    time_diff_value = forms.ChoiceField(
        choices=TIME_CHOICES,
        initial='days',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    model_type = forms.ChoiceField(
        choices=MODEL_CHOICES,
        initial='RandomForestRegressor',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
