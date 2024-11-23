from django.apps import AppConfig
import threading
import time
import os


class Analytics2Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics2'
    
    def ready(self):
        # 메인 프로세스에서만 실행되도록 확인
        if os.environ.get('RUN_MAIN') != 'true':
            return
            
        def delayed_start():
            # 서버가 완전히 시작될 때까지 잠시 대기
            time.sleep(5)
            # 분석 시작
            from .views import start_scheduler
            start_scheduler()

        # 백그라운드 스레드에서 분석 실행
        thread = threading.Thread(target=delayed_start)
        thread.daemon = True
        thread.start()
