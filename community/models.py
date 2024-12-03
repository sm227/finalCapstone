from django.db import models
from django.contrib.auth.models import User


class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True)  # 주식 종목 심볼
    name = models.CharField(max_length=255)  # 주식 이름
    price = models.FloatField()  # 주식 가격 (예시)

    def __str__(self):
        return self.name


class PollOption(models.Model):
    comment = models.ForeignKey('Comment', related_name='poll_options', on_delete=models.CASCADE)
    text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)


class PollVote(models.Model):
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE)
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('option', 'user')


# 댓글 모델 수정
class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="comments", default=1)  # 주식과 연결
    text = models.TextField()
    image = models.ImageField(upload_to='comments/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    likes = models.ManyToManyField(User, related_name='liked_comments', blank=True)
    dislikes = models.ManyToManyField(User, related_name='disliked_comments', blank=True)
    is_poll = models.BooleanField(default=False)

    # stock_symbol = models.CharField(max_length=10)

    def total_likes(self):
        return self.likes.count()

    def total_dislikes(self):
        return self.dislikes.count()

    def __str__(self):
        return f"{self.user.username}: {self.text[:20]}"

# 주식 정보 모델
