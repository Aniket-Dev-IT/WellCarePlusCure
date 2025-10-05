from rest_framework import serializers
from .models import (
    Notification, NotificationPreference, NotificationType, 
    DeviceToken, NotificationLog
)


class NotificationTypeSerializer(serializers.ModelSerializer):
    """Serializer for notification types"""
    
    class Meta:
        model = NotificationType
        fields = [
            'id', 'name', 'description', 'default_email_enabled',
            'default_sms_enabled', 'default_push_enabled'
        ]
        read_only_fields = ['id']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for notifications"""
    
    notification_type = NotificationTypeSerializer(read_only=True)
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'notification_type',
            'title', 'message', 'priority', 'extra_data',
            'email_status', 'sms_status', 'push_status',
            'is_read', 'created_at', 'scheduled_at', 'sent_at', 'read_at'
        ]
        read_only_fields = [
            'id', 'recipient', 'recipient_name', 'notification_type',
            'email_status', 'sms_status', 'push_status', 'is_read',
            'created_at', 'scheduled_at', 'sent_at', 'read_at'
        ]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """Serializer for notification preferences"""
    
    notification_type = NotificationTypeSerializer(read_only=True)
    notification_type_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = NotificationPreference
        fields = [
            'id', 'user', 'notification_type', 'notification_type_id',
            'email_enabled', 'sms_enabled', 'push_enabled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class DeviceTokenSerializer(serializers.ModelSerializer):
    """Serializer for device tokens"""
    
    class Meta:
        model = DeviceToken
        fields = [
            'id', 'user', 'token', 'platform', 'is_active',
            'created_at', 'last_used_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'last_used_at']


class NotificationLogSerializer(serializers.ModelSerializer):
    """Serializer for notification logs"""
    
    class Meta:
        model = NotificationLog
        fields = [
            'id', 'notification', 'action', 'channel',
            'details', 'timestamp'
        ]
        read_only_fields = ['id', 'notification', 'timestamp']
