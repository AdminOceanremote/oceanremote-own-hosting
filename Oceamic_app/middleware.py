from django.utils import timezone
from django.db import models
from .models import UserActivity

class ActivityTrackerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Get or create with atomic update
            obj, created = UserActivity.objects.get_or_create(
                user=request.user,
                defaults={
                    'page_views': 1,
                    'last_activity': timezone.now(),
                    'last_login': timezone.now()
                }
            )
            if not created:
                UserActivity.objects.filter(pk=obj.pk).update(
                    page_views=models.F('page_views') + 1,
                    last_activity=timezone.now()
                )
        return self.get_response(request)