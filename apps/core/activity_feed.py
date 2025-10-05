"""
Activity Feed Service
Tracks and displays system-wide activities and events in real-time
"""

from datetime import datetime, timedelta
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from apps.users.models import UserProfile
from apps.doctors.models import Doctor, Appointment, Review


class ActivityFeedManager:
    """
    Manages activity feeds for different user types
    """
    
    def __init__(self, user=None, limit=50):
        self.user = user
        self.limit = limit
        self.today = timezone.now().date()
        
    def get_patient_activity_feed(self, patient_user):
        """Get activity feed for a specific patient"""
        activities = []
        
        # Recent appointments
        appointments = Appointment.objects.filter(
            patient=patient_user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('doctor__user').order_by('-created_at')[:10]
        
        for appointment in appointments:
            status_icon = self._get_appointment_status_icon(appointment.status)
            activities.append({
                'type': 'appointment',
                'icon': status_icon,
                'title': f"Appointment {appointment.get_status_display().lower()}",
                'description': f"with Dr. {appointment.doctor.user.get_full_name()} - {appointment.appointment_type}",
                'timestamp': appointment.created_at,
                'date': appointment.created_at,
                'url': f'/appointments/{appointment.id}/',
                'priority': self._get_appointment_priority(appointment.status)
            })
        
        # Recent reviews given
        reviews = Review.objects.filter(
            patient=patient_user,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('doctor__user').order_by('-created_at')[:5]
        
        for review in reviews:
            activities.append({
                'type': 'review',
                'icon': 'bi-star-fill',
                'title': f"Review submitted ({review.overall_rating}⭐)",
                'description': f"for Dr. {review.doctor.user.get_full_name()}",
                'timestamp': review.created_at,
                'date': review.created_at,
                'url': f'/doctors/{review.doctor.id}/#reviews',
                'priority': 'normal'
            })
        
        # Profile updates
        try:
            profile = UserProfile.objects.get(user=patient_user)
            if profile.updated_at and profile.updated_at >= timezone.now() - timedelta(days=30):
                activities.append({
                    'type': 'profile',
                    'icon': 'bi-person-gear',
                    'title': "Profile updated",
                    'description': "Your profile information was updated",
                    'timestamp': profile.updated_at,
                    'date': profile.updated_at,
                    'url': '/profile/',
                    'priority': 'low'
                })
        except UserProfile.DoesNotExist:
            pass
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:self.limit]
    
    def get_doctor_activity_feed(self, doctor_user):
        """Get activity feed for a specific doctor"""
        activities = []
        
        try:
            doctor = Doctor.objects.get(user=doctor_user)
        except Doctor.DoesNotExist:
            return activities
        
        # Recent appointments
        appointments = Appointment.objects.filter(
            doctor=doctor,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('patient').order_by('-created_at')[:15]
        
        for appointment in appointments:
            status_icon = self._get_appointment_status_icon(appointment.status)
            activities.append({
                'type': 'appointment',
                'icon': status_icon,
                'title': f"New appointment {appointment.get_status_display().lower()}",
                'description': f"with {appointment.patient.get_full_name()} - {appointment.appointment_type}",
                'timestamp': appointment.created_at,
                'date': appointment.created_at,
                'url': f'/doctor/appointments/{appointment.id}/',
                'priority': self._get_appointment_priority(appointment.status)
            })
        
        # Recent reviews received
        reviews = Review.objects.filter(
            doctor=doctor,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('patient').order_by('-created_at')[:10]
        
        for review in reviews:
            rating_color = 'success' if review.overall_rating >= 4 else 'warning' if review.overall_rating >= 3 else 'danger'
            activities.append({
                'type': 'review',
                'icon': 'bi-star-fill',
                'title': f"New review received ({review.overall_rating}⭐)",
                'description': f"from {review.patient.get_full_name()}",
                'timestamp': review.created_at,
                'date': review.created_at,
                'url': f'/doctor/reviews/',
                'priority': 'high' if review.overall_rating >= 4 else 'normal',
                'color': rating_color
            })
        
        # Profile verification updates
        if doctor.verified and doctor.updated_at >= timezone.now() - timedelta(days=30):
            activities.append({
                'type': 'verification',
                'icon': 'bi-patch-check-fill',
                'title': "Profile verified",
                'description': "Your doctor profile has been verified",
                'timestamp': doctor.updated_at,
                'date': doctor.updated_at,
                'url': '/doctor/profile/',
                'priority': 'high',
                'color': 'success'
            })
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:self.limit]
    
    def get_system_activity_feed(self):
        """Get system-wide activity feed for admin"""
        activities = []
        
        # Recent user registrations
        recent_users = User.objects.filter(
            date_joined__gte=timezone.now() - timedelta(days=7)
        ).order_by('-date_joined')[:10]
        
        for user in recent_users:
            is_doctor = hasattr(user, 'doctor')
            activities.append({
                'type': 'user_registration',
                'icon': 'bi-person-plus' if not is_doctor else 'bi-person-badge',
                'title': f"New {'doctor' if is_doctor else 'user'} registered",
                'description': f"{user.get_full_name() or user.username}",
                'timestamp': user.date_joined,
                'date': user.date_joined,
                'url': f'/admin/auth/user/{user.id}/change/',
                'priority': 'high' if is_doctor else 'normal'
            })
        
        # Recent appointments
        recent_appointments = Appointment.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).select_related('patient', 'doctor__user').order_by('-created_at')[:15]
        
        for appointment in recent_appointments:
            status_icon = self._get_appointment_status_icon(appointment.status)
            activities.append({
                'type': 'appointment',
                'icon': status_icon,
                'title': f"Appointment {appointment.get_status_display().lower()}",
                'description': f"{appointment.patient.get_full_name()} → Dr. {appointment.doctor.user.get_full_name()}",
                'timestamp': appointment.created_at,
                'date': appointment.created_at,
                'url': f'/admin/doctors/appointment/{appointment.id}/change/',
                'priority': self._get_appointment_priority(appointment.status)
            })
        
        # Recent reviews
        recent_reviews = Review.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=1)
        ).select_related('patient', 'doctor__user').order_by('-created_at')[:10]
        
        for review in recent_reviews:
            activities.append({
                'type': 'review',
                'icon': 'bi-star-fill',
                'title': f"New review ({review.overall_rating}⭐)",
                'description': f"{review.patient.get_full_name()} reviewed Dr. {review.doctor.user.get_full_name()}",
                'timestamp': review.created_at,
                'date': review.created_at,
                'url': f'/admin/doctors/review/{review.id}/change/',
                'priority': 'normal'
            })
        
        # Sort by timestamp and limit
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        return activities[:self.limit]
    
    def get_trending_activities(self, days=7):
        """Get trending activities and statistics"""
        start_date = timezone.now() - timedelta(days=days)
        
        # Most active doctors
        active_doctors = Doctor.objects.filter(
            appointments__created_at__gte=start_date
        ).annotate(
            appointment_count=models.Count('appointments')
        ).order_by('-appointment_count')[:5]
        
        # Most reviewed doctors
        reviewed_doctors = Doctor.objects.filter(
            reviews__created_at__gte=start_date
        ).annotate(
            review_count=models.Count('reviews'),
            avg_rating=models.Avg('reviews__overall_rating')
        ).order_by('-review_count')[:5]
        
        # Popular specialties
        from django.db import models
        popular_specialties = Doctor.objects.filter(
            appointments__created_at__gte=start_date
        ).values('specialization').annotate(
            appointment_count=models.Count('appointments')
        ).order_by('-appointment_count')[:5]
        
        return {
            'active_doctors': [{
                'name': doc.user.get_full_name(),
                'specialty': doc.specialization,
                'count': doc.appointment_count
            } for doc in active_doctors],
            'reviewed_doctors': [{
                'name': doc.user.get_full_name(),
                'specialty': doc.specialization,
                'reviews': doc.review_count,
                'rating': round(doc.avg_rating, 1) if doc.avg_rating else 0
            } for doc in reviewed_doctors],
            'popular_specialties': list(popular_specialties)
        }
    
    def _get_appointment_status_icon(self, status):
        """Get appropriate icon for appointment status"""
        status_icons = {
            'pending': 'bi-clock',
            'confirmed': 'bi-check-circle',
            'completed': 'bi-check-circle-fill',
            'cancelled': 'bi-x-circle',
            'rescheduled': 'bi-arrow-repeat'
        }
        return status_icons.get(status, 'bi-calendar')
    
    def _get_appointment_priority(self, status):
        """Get priority level for appointment status"""
        priority_map = {
            'pending': 'high',
            'confirmed': 'normal',
            'completed': 'low',
            'cancelled': 'high',
            'rescheduled': 'normal'
        }
        return priority_map.get(status, 'normal')


class ActivityNotificationService:
    """
    Service for creating and managing activity notifications
    """
    
    @staticmethod
    def create_appointment_notification(appointment, action='created'):
        """Create notification for appointment-related activities"""
        # This would integrate with a notification system
        # For now, we'll just log the activity
        return {
            'type': 'appointment_notification',
            'user_id': appointment.patient.id,
            'message': f"Appointment {action} with Dr. {appointment.doctor.user.get_full_name()}",
            'data': {
                'appointment_id': appointment.id,
                'action': action,
                'doctor_name': appointment.doctor.user.get_full_name()
            }
        }
    
    @staticmethod
    def create_review_notification(review):
        """Create notification for new review"""
        return {
            'type': 'review_notification',
            'user_id': review.doctor.user.id,
            'message': f"New {review.overall_rating}⭐ review from {review.patient.get_full_name()}",
            'data': {
                'review_id': review.id,
                'rating': review.overall_rating,
                'patient_name': review.patient.get_full_name()
            }
        }
    
    @staticmethod
    def create_system_notification(message, notification_type='info', users=None):
        """Create system-wide notification"""
        return {
            'type': 'system_notification',
            'message': message,
            'notification_type': notification_type,
            'timestamp': timezone.now(),
            'users': users or []
        }


def get_user_activity_context(user, activity_type='patient'):
    """
    Get activity context for templates
    """
    feed_manager = ActivityFeedManager(user=user, limit=20)
    
    if activity_type == 'patient':
        activities = feed_manager.get_patient_activity_feed(user)
    elif activity_type == 'doctor':
        activities = feed_manager.get_doctor_activity_feed(user)
    elif activity_type == 'admin':
        activities = feed_manager.get_system_activity_feed()
    else:
        activities = []
    
    return {
        'recent_activity': activities,
        'activity_count': len(activities),
        'trending_activities': feed_manager.get_trending_activities() if activity_type == 'admin' else None
    }
