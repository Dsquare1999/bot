from rest_framework import serializers
from .models import Notification
from .functions import send_notification_to_user

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        notification = super().create(validated_data)
        
        send_notification_to_user(notification.user.id, notification.message)
        return notification
