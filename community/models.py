from django.db import models
from django.contrib.auth.models import User

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)  # 주식 종목 심볼
    name = models.CharField(max_length=255)  # 주식 이름
    price = models.FloatField()  # 주식 가격 (예시)

    def __str__(self):
        return self.name

# 댓글 모델 수정
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="comments", default=1)  # 주식과 연결
    text = models.TextField()
    image = models.ImageField(upload_to='comments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.text[:20]}"

# 주식 정보 모델

