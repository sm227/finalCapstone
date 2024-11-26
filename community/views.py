from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from login.models import UserProfile
# Create your views here.

@login_required
def community(request):
    return render(request, 'community/community.html')