"""
Admin System Signals
Track user activities and create system alerts
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from .models import AdminActivity, SystemAlert
from apps.doctors.models import Doctor, Appointment
from apps.users.models import UserProfile
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get the real client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip


def log_admin_activity(admin_user, action_type, description, content_object=None, request=None, metadata=None):
    """Helper function to log admin activities"""
    if not admin_user.is_staff:
        return
    
    try:
        ip_address = get_client_ip(request) if request else '127.0.0.1'
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        activity = AdminActivity.objects.create(
            admin=admin_user,
            action_type=action_type,
            description=description,
            content_object=content_object,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata or {}
        )
        logger.info(f"Admin activity logged: {activity}")
    except Exception as e:
        logger.error(f"Failed to log admin activity: {e}")


@receiver(user_logged_in)
def log_admin_login(sender, request, user, **kwargs):
    """Log admin login activities"""
    if user.is_staff:
        log_admin_activity(
            admin_user=user,
            action_type='login',
            description=f"Admin {user.username} logged in",
            request=request,
            metadata={'login_time': timezone.now().isoformat()}
        )


@receiver(user_logged_out)
def log_admin_logout(sender, request, user, **kwargs):
    """Log admin logout activities"""
    if user and user.is_staff:
        log_admin_activity(
            admin_user=user,
            action_type='logout',
            description=f"Admin {user.username} logged out",
            request=request,
            metadata={'logout_time': timezone.now().isoformat()}
        )


@receiver(post_save, sender=User)
def track_user_changes(sender, instance, created, **kwargs):
    """Track user creation and modifications"""
    # Get the current request to identify the admin
    # This is a simplified version - in practice, you'd use thread-local storage
    # or pass the admin user context differently
    
    action_type = 'create' if created else 'update'
    description = f"User {instance.username} was {'created' if created else 'updated'}"
    
    # Create system alert for new user registrations
    if created and not instance.is_staff:
        SystemAlert.objects.create(
            title=f"New User Registration: {instance.username}",
            message=f"A new user {instance.get_full_name() or instance.username} has registered.",
            alert_type='user_activity',
            severity='low',
            content_object=instance
        )


@receiver(post_save, sender=Doctor)
def track_doctor_changes(sender, instance, created, **kwargs):
    """Track doctor creation and modifications"""
    action_type = 'create' if created else 'update'
    
    if created:
        # Create alert for new doctor registration
        SystemAlert.objects.create(
            title=f"New Doctor Registration: {instance.display_name}",
            message=f"A new doctor {instance.display_name} has registered and requires verification.",
            alert_type='doctor_activity',
            severity='medium',
            content_object=instance,
            metadata={'requires_verification': True}
        )
    
    # Check for important status changes
    if not created:
        # If doctor becomes available/unavailable
        if hasattr(instance, '_previous_availability'):
            if instance.is_available != instance._previous_availability:
                status = 'available' if instance.is_available else 'unavailable'
                SystemAlert.objects.create(
                    title=f"Doctor Status Changed: {instance.display_name}",
                    message=f"Dr. {instance.display_name} is now {status}",
                    alert_type='doctor_activity',
                    severity='low',
                    content_object=instance
                )


@receiver(pre_save, sender=Doctor)
def store_previous_doctor_state(sender, instance, **kwargs):
    """Store previous doctor state for comparison"""
    if instance.pk:
        try:
            previous = Doctor.objects.get(pk=instance.pk)
            instance._previous_availability = previous.is_available
        except Doctor.DoesNotExist:
            pass


@receiver(post_save, sender=Appointment)
def track_appointment_changes(sender, instance, created, **kwargs):
    """Track appointment creation and modifications"""
    if created:
        # Alert for new appointments
        SystemAlert.objects.create(
            title=f"New Appointment: {instance.doctor.display_name}",
            message=f"New appointment booked with Dr. {instance.doctor.display_name} for {instance.appointment_date}",
            alert_type='appointment',
            severity='low',
            content_object=instance
        )
    else:
        # Check for status changes
        if hasattr(instance, '_previous_status'):
            if instance.status != instance._previous_status:
                severity = 'medium' if instance.status == 'cancelled' else 'low'
                SystemAlert.objects.create(
                    title=f"Appointment Status Changed",
                    message=f"Appointment with Dr. {instance.doctor.display_name} changed from {instance._previous_status} to {instance.status}",
                    alert_type='appointment',
                    severity=severity,
                    content_object=instance
                )


@receiver(pre_save, sender=Appointment)
def store_previous_appointment_state(sender, instance, **kwargs):
    """Store previous appointment state for comparison"""
    if instance.pk:
        try:
            previous = Appointment.objects.get(pk=instance.pk)
            instance._previous_status = previous.status
        except Appointment.DoesNotExist:
            pass


# Create system alerts for important events
def create_security_alert(title, message, severity='medium', metadata=None):
    """Create security alerts"""
    SystemAlert.objects.create(
        title=title,
        message=message,
        alert_type='security',
        severity=severity,
        metadata=metadata or {}
    )


def create_system_alert(title, message, severity='low', metadata=None):
    """Create general system alerts"""
    SystemAlert.objects.create(
        title=title,
        message=message,
        alert_type='system',
        severity=severity,
        metadata=metadata or {}
    )
