from django.urls import re_path
from notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    re_path(r'ws/notifications/(?P<user_id>[0-9a-fA-F-]+)/$', NotificationConsumer.as_asgi()),

]
