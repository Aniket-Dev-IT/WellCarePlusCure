from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import json


class NotificationType(models.Model):
    """Define different types of notifications"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    default_email_enabled = models.BooleanField(default=True)
    default_sms_enabled = models.BooleanField(default=False)
    default_push_enabled = models.BooleanField(default=True)
    
    # Templates
    email_subject_template = models.CharField(max_length=200, blank=True)
    email_body_template = models.TextField(blank=True)
    sms_template = models.CharField(max_length=160, blank=True)
    push_title_template = models.CharField(max_length=100, blank=True)
    push_body_template = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Notification Type"
        verbose_name_plural = "Notification Types"
        
    def __str__(self):
        return self.name


class NotificationPreference(models.Model):
    """User preferences for different notification types"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'notification_type')
        verbose_name = "Notification Preference"
        verbose_name_plural = "Notification Preferences"
        
    def __str__(self):
        return f"{self.user.username} - {self.notification_type.name}"


class Notification(models.Model):
    """Individual notification instances"""
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read'),
    ]
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    
    # Generic relation to any model
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Additional data as JSON
    extra_data = models.JSONField(default=dict, blank=True)
    
    # Delivery status
    email_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    sms_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    push_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.recipient.username}"
    
    def mark_as_read(self):
        """Mark notification as read"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=['read_at'])
    
    @property
    def is_read(self):
        return self.read_at is not None
    
    @property
    def is_overdue(self):
        if self.scheduled_at and timezone.now() > self.scheduled_at:
            return self.email_status == 'pending' or self.sms_status == 'pending' or self.push_status == 'pending'
        return False


class NotificationTemplate(models.Model):
    """Customizable notification templates"""
    name = models.CharField(max_length=100, unique=True)
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE, related_name='templates')
    
    # Template content
    subject_template = models.CharField(max_length=200)
    body_template = models.TextField()
    
    # Supported languages
    language = models.CharField(max_length=10, default='en')
    
    # Template variables (JSON format)
    variables = models.JSONField(default=list, help_text="List of template variables available")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('name', 'language')
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
        
    def __str__(self):
        return f"{self.name} ({self.language})"


class NotificationQueue(models.Model):
    """Queue for batch processing notifications"""
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE)
    
    # Delivery methods to attempt
    send_email = models.BooleanField(default=False)
    send_sms = models.BooleanField(default=False)
    send_push = models.BooleanField(default=False)
    
    # Processing info
    attempts = models.PositiveIntegerField(default=0)
    max_attempts = models.PositiveIntegerField(default=3)
    next_attempt_at = models.DateTimeField(default=timezone.now)
    last_error = models.TextField(blank=True)
    
    processed = models.BooleanField(default=False)
    processed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification Queue"
        verbose_name_plural = "Notification Queue"
        ordering = ['next_attempt_at']
        
    def __str__(self):
        return f"Queue: {self.notification.title}"
    
    def increment_attempts(self, error_message=""):
        """Increment attempt count and set next attempt time"""
        self.attempts += 1
        self.last_error = error_message
        
        if self.attempts >= self.max_attempts:
            self.processed = True
            self.processed_at = timezone.now()
        else:
            # Exponential backoff: 5 min, 15 min, 45 min
            delay_minutes = 5 * (3 ** (self.attempts - 1))
            self.next_attempt_at = timezone.now() + timezone.timedelta(minutes=delay_minutes)
        
        self.save()


class NotificationLog(models.Model):
    """Log all notification activities"""
    ACTION_CHOICES = [
        ('created', 'Created'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('read', 'Read'),
        ('clicked', 'Clicked'),
    ]
    
    notification = models.ForeignKey(Notification, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    channel = models.CharField(max_length=20, choices=[('email', 'Email'), ('sms', 'SMS'), ('push', 'Push')])
    
    details = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notification Log"
        verbose_name_plural = "Notification Logs"
        ordering = ['-timestamp']
        
    def __str__(self):
        return f"{self.notification.title} - {self.action} via {self.channel}"


class DeviceToken(models.Model):
    """Store device tokens for push notifications"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='device_tokens')
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=20, choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')])
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ('user', 'token')
        verbose_name = "Device Token"
        verbose_name_plural = "Device Tokens"
        
    def __str__(self):
        return f"{self.user.username} - {self.platform}"
