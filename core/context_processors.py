from core.models import Notification


def notifications(request):
    if not request.user.is_authenticated:
        return {}
    qs = Notification.objects.filter(user=request.user, is_read=False)
    return {"unread_notifications": qs[:10], "unread_count": qs.count()}
