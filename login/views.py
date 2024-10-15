from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserProfile


def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        api_key = request.POST['api_key']
        api_secret = request.POST['api_secret']
        acc_num = request.POST['acc_num']

        if User.objects.filter(username=username).exists():
            messages.error(request, '이미 존재하는 사용자명입니다.')
            return render(request, 'login/signup.html')

        user = User.objects.create_user(username=username, password=password)
        UserProfile.objects.create(user=user, api_key=api_key, api_secret=api_secret, acc_num=acc_num)

        messages.success(request, '회원가입이 완료되었습니다. 로그인해주세요.')
        return redirect('login')

    return render(request, 'login/signup.html')


def user_login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, '로그인되었습니다.')
            return redirect('dashboard')  # 대시보드 페이지로 리다이렉트
        else:
            messages.error(request, '아이디 또는 비밀번호가 올바르지 않습니다.')

    return render(request, 'login/login.html')


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "성공적으로 로그아웃되었습니다.")
    return redirect('login')  # 로
