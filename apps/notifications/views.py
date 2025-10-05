from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, UpdateView, TemplateView
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import (
    Notification, NotificationPreference, NotificationType, 
    DeviceToken, NotificationLog
)
from .services import NotificationService
from .serializers import NotificationSerializer, NotificationPreferenceSerializer
import json
import logging


logger = logging.getLogger(__name__)


class NotificationListView(LoginRequiredMixin, ListView):
    """List view for user notifications"""
    model = Notification
    template_name = 'notifications/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 20
    
    def get_queryset(self):
        """Get notifications for current user"""
        queryset = Notification.objects.filter(
            recipient=self.request.user
        ).select_related('notification_type').order_by('-created_at')
        
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter == 'unread':
            queryset = queryset.filter(read_at__isnull=True)
        elif status_filter == 'read':
            queryset = queryset.filter(read_at__isnull=False)
        
        # Filter by type
        type_filter = self.request.GET.get('type')
        if type_filter:
            queryset = queryset.filter(notification_type__name=type_filter)
        
        # Filter by priority
        priority_filter = self.request.GET.get('priority')
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        context['notification_types'] = NotificationType.objects.all()
        context['priority_choices'] = Notification.PRIORITY_CHOICES
        
        # Get counts
        user_notifications = Notification.objects.filter(recipient=self.request.user)
        context['total_count'] = user_notifications.count()
        context['unread_count'] = user_notifications.filter(read_at__isnull=True).count()
        context['read_count'] = user_notifications.filter(read_at__isnull=False).count()
        
        # Current filters
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_type'] = self.request.GET.get('type', '')
        context['current_priority'] = self.request.GET.get('priority', '')
        
        return context


class NotificationDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a single notification"""
    model = Notification
    template_name = 'notifications/notification_detail.html'
    context_object_name = 'notification'
    
    def get_queryset(self):
        """Ensure user can only see their own notifications"""
        return Notification.objects.filter(recipient=self.request.user)
    
    def get_object(self):
        """Mark notification as read when viewed"""
        obj = super().get_object()
        if not obj.is_read:
            obj.mark_as_read()
        return obj


class NotificationPreferencesView(LoginRequiredMixin, TemplateView):
    """View for managing notification preferences"""
    template_name = 'notifications/preferences.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all notification types
        notification_types = NotificationType.objects.all()
        user_preferences = {}
        
        # Get existing preferences
        for notif_type in notification_types:
            try:
                pref = NotificationPreference.objects.get(
                    user=self.request.user,
                    notification_type=notif_type
                )
                user_preferences[notif_type.id] = {
                    'email': pref.email_enabled,
                    'sms': pref.sms_enabled,
                    'push': pref.push_enabled,
                }
            except NotificationPreference.DoesNotExist:
                user_preferences[notif_type.id] = {
                    'email': notif_type.default_email_enabled,
                    'sms': notif_type.default_sms_enabled,
                    'push': notif_type.default_push_enabled,
                }
        
        context['notification_types'] = notification_types
        context['user_preferences'] = user_preferences
        return context
    
    def post(self, request):
        """Handle preference updates"""
        try:
            notification_types = NotificationType.objects.all()
            
            for notif_type in notification_types:
                email_enabled = request.POST.get(f'email_{notif_type.id}') == 'on'
                sms_enabled = request.POST.get(f'sms_{notif_type.id}') == 'on'
                push_enabled = request.POST.get(f'push_{notif_type.id}') == 'on'
                
                # Update or create preference
                NotificationPreference.objects.update_or_create(
                    user=request.user,
                    notification_type=notif_type,
                    defaults={
                        'email_enabled': email_enabled,
                        'sms_enabled': sms_enabled,
                        'push_enabled': push_enabled,
                    }
                )
            
            messages.success(request, 'Notification preferences updated successfully!')
            
        except Exception as e:
            logger.error(f"Error updating preferences for {request.user.username}: {str(e)}")
            messages.error(request, 'Error updating preferences. Please try again.')
        
        return redirect('notifications:preferences')


# AJAX Views
@login_required
@require_POST
def mark_as_read(request, notification_id):
    """Mark a notification as read via AJAX"""
    try:
        notification = get_object_or_404(
            Notification,
            id=notification_id,
            recipient=request.user
        )
        
        notification.mark_as_read()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification marked as read'
        })
    
    except Exception as e:
        logger.error(f"Error marking notification {notification_id} as read: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error marking notification as read'
        }, status=500)


@login_required
@require_POST
def mark_all_as_read(request):
    """Mark all notifications as read for current user"""
    try:
        unread_notifications = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        )
        
        count = unread_notifications.count()
        unread_notifications.update(read_at=timezone.now())
        
        return JsonResponse({
            'success': True,
            'message': f'Marked {count} notifications as read',
            'count': count
        })
    
    except Exception as e:
        logger.error(f"Error marking all notifications as read for {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error marking notifications as read'
        }, status=500)


@login_required
def get_unread_count(request):
    """Get unread notification count for current user"""
    try:
        count = Notification.objects.filter(
            recipient=request.user,
            read_at__isnull=True
        ).count()
        
        return JsonResponse({
            'success': True,
            'count': count
        })
    
    except Exception as e:
        logger.error(f"Error getting unread count for {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error getting notification count'
        }, status=500)


@login_required
def get_recent_notifications(request):
    """Get recent notifications for current user"""
    try:
        limit = int(request.GET.get('limit', 5))
        
        notifications = Notification.objects.filter(
            recipient=request.user
        ).select_related('notification_type').order_by('-created_at')[:limit]
        
        notification_data = []
        for notif in notifications:
            notification_data.append({
                'id': notif.id,
                'title': notif.title,
                'message': notif.message[:100] + '...' if len(notif.message) > 100 else notif.message,
                'type': notif.notification_type.name,
                'priority': notif.priority,
                'is_read': notif.is_read,
                'created_at': notif.created_at.isoformat(),
                'url': f'/notifications/{notif.id}/'
            })
        
        return JsonResponse({
            'success': True,
            'notifications': notification_data
        })
    
    except Exception as e:
        logger.error(f"Error getting recent notifications for {request.user.username}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error getting notifications'
        }, status=500)


@csrf_exempt
@require_POST
def register_device_token(request):
    """Register device token for push notifications"""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required'
            }, status=401)
        
        data = json.loads(request.body)
        token = data.get('token')
        platform = data.get('platform', 'web')
        
        if not token:
            return JsonResponse({
                'success': False,
                'message': 'Token is required'
            }, status=400)
        
        # Create or update device token
        device_token, created = DeviceToken.objects.get_or_create(
            user=request.user,
            token=token,
            defaults={'platform': platform, 'is_active': True}
        )
        
        if not created:
            device_token.platform = platform
            device_token.is_active = True
            device_token.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Device token registered successfully'
        })
    
    except Exception as e:
        logger.error(f"Error registering device token: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error registering device token'
        }, status=500)


# API Viewsets for REST API
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """API viewset for notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get notifications for authenticated user"""
        # Handle schema generation when user is anonymous
        if getattr(self, 'swagger_fake_view', False):
            return Notification.objects.none()
        
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related('notification_type').order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.mark_as_read()
        
        return Response({
            'success': True,
            'message': 'Notification marked as read'
        })
    
    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read"""
        unread_notifications = self.get_queryset().filter(read_at__isnull=True)
        count = unread_notifications.count()
        unread_notifications.update(read_at=timezone.now())
        
        return Response({
            'success': True,
            'message': f'Marked {count} notifications as read',
            'count': count
        })
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread notification count"""
        count = self.get_queryset().filter(read_at__isnull=True).count()
        
        return Response({
            'success': True,
            'count': count
        })


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """API viewset for notification preferences"""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Get preferences for authenticated user"""
        # Handle schema generation when user is anonymous
        if getattr(self, 'swagger_fake_view', False):
            return NotificationPreference.objects.none()
        
        return NotificationPreference.objects.filter(
            user=self.request.user
        ).select_related('notification_type')


# Admin views for managing notifications
@login_required
def admin_notification_dashboard(request):
    """Admin dashboard for notification management"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin privileges required.')
        return redirect('home')
    
    # Get statistics
    stats = {
        'total_notifications': Notification.objects.count(),
        'pending_notifications': Notification.objects.filter(
            email_status='pending'
        ).count(),
        'failed_notifications': Notification.objects.filter(
            Q(email_status='failed') | Q(sms_status='failed') | Q(push_status='failed')
        ).count(),
        'notification_types': NotificationType.objects.count(),
        'active_users': Notification.objects.values('recipient').distinct().count(),
    }
    
    # Recent activity
    recent_notifications = Notification.objects.select_related(
        'notification_type', 'recipient'
    ).order_by('-created_at')[:10]
    
    # Notification logs
    recent_logs = NotificationLog.objects.select_related(
        'notification'
    ).order_by('-timestamp')[:20]
    
    context = {
        'stats': stats,
        'recent_notifications': recent_notifications,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'notifications/admin_dashboard.html', context)


@login_required
@require_POST
def send_bulk_notification(request):
    """Send bulk notifications (admin only)"""
    if not request.user.is_staff:
        return JsonResponse({
            'success': False,
            'message': 'Access denied'
        }, status=403)
    
    try:
        data = json.loads(request.body)
        
        recipient_type = data.get('recipient_type', 'all')  # all, patients, doctors
        notification_type = data.get('notification_type', 'announcement')
        title = data.get('title', '')
        message = data.get('message', '')
        priority = data.get('priority', 'normal')
        
        if not title or not message:
            return JsonResponse({
                'success': False,
                'message': 'Title and message are required'
            }, status=400)
        
        # Get recipients
        from django.contrib.auth.models import User
        if recipient_type == 'patients':
            recipients = User.objects.filter(
                userprofile__isnull=False
            )
        elif recipient_type == 'doctors':
            recipients = User.objects.filter(
                doctor__isnull=False
            )
        else:
            recipients = User.objects.all()
        
        # Send notifications
        service = NotificationService()
        notifications = service.bulk_create_notifications(
            recipients=list(recipients),
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Sent {len(notifications)} notifications successfully',
            'count': len(notifications)
        })
    
    except Exception as e:
        logger.error(f"Error sending bulk notifications: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': 'Error sending notifications'
        }, status=500)


# Webhook endpoints for delivery status updates
@csrf_exempt
@require_POST
def email_webhook(request):
    """Handle email delivery status webhooks"""
    try:
        data = json.loads(request.body)
        
        # Process email delivery status
        # This would be called by your email provider (e.g., SendGrid, Mailgun)
        notification_id = data.get('notification_id')
        status = data.get('status')  # delivered, bounced, opened, etc.
        
        if notification_id and status:
            try:
                notification = Notification.objects.get(id=notification_id)
                
                if status == 'delivered':
                    notification.email_status = 'delivered'
                elif status in ['bounced', 'dropped']:
                    notification.email_status = 'failed'
                
                notification.save()
                
                # Log the event
                NotificationLog.objects.create(
                    notification=notification,
                    action=status,
                    channel='email',
                    details=data
                )
                
            except Notification.DoesNotExist:
                logger.warning(f"Notification {notification_id} not found for email webhook")
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        logger.error(f"Error processing email webhook: {str(e)}")
        return JsonResponse({'success': False}, status=500)


@csrf_exempt
@require_POST
def sms_webhook(request):
    """Handle SMS delivery status webhooks"""
    try:
        data = json.loads(request.body)
        
        # Process SMS delivery status
        notification_id = data.get('notification_id')
        status = data.get('status')  # delivered, failed, etc.
        
        if notification_id and status:
            try:
                notification = Notification.objects.get(id=notification_id)
                
                if status == 'delivered':
                    notification.sms_status = 'delivered'
                elif status == 'failed':
                    notification.sms_status = 'failed'
                
                notification.save()
                
                # Log the event
                NotificationLog.objects.create(
                    notification=notification,
                    action=status,
                    channel='sms',
                    details=data
                )
                
            except Notification.DoesNotExist:
                logger.warning(f"Notification {notification_id} not found for SMS webhook")
        
        return JsonResponse({'success': True})
    
    except Exception as e:
        logger.error(f"Error processing SMS webhook: {str(e)}")
        return JsonResponse({'success': False}, status=500)
