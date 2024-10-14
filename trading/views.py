from django.shortcuts import render

def trading(request):
    return render(request, 'trading/trading.html')
