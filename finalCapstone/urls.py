"""
URL configuration for finalCapstone project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

app_name = "main"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('dashboard/', include('dashboard.urls'), name="dashboard"),
    path('', include('landing.urls')),
    path('', include('dashboard.urls')),
    path('articles/', include('articles.urls')),
    path('trading/', include('trading.urls')),
    path('accounts/', include('login.urls')),
]
