from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'notifications'

# API Router
router = DefaultRouter()
router.register(r'api/notifications', views.NotificationViewSet, basename='notification-api')
router.register(r'api/preferences', views.NotificationPreferenceViewSet, basename='preference-api')

urlpatterns = [
    # Main notification views
    path('', views.NotificationListView.as_view(), name='list'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='detail'),
    path('preferences/', views.NotificationPreferencesView.as_view(), name='preferences'),
    
    # AJAX endpoints
    path('ajax/mark-read/<int:notification_id>/', views.mark_as_read, name='mark-read'),
    path('ajax/mark-all-read/', views.mark_all_as_read, name='mark-all-read'),
    path('ajax/unread-count/', views.get_unread_count, name='unread-count'),
    path('ajax/recent/', views.get_recent_notifications, name='recent'),
    path('ajax/register-device/', views.register_device_token, name='register-device'),
    
    # Admin views
    path('admin/dashboard/', views.admin_notification_dashboard, name='admin-dashboard'),
    path('admin/send-bulk/', views.send_bulk_notification, name='send-bulk'),
    
    # Webhook endpoints
    path('webhooks/email/', views.email_webhook, name='email-webhook'),
    path('webhooks/sms/', views.sms_webhook, name='sms-webhook'),
    
    # API routes
    path('', include(router.urls)),
]
