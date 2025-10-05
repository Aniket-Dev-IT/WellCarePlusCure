"""
Admin Analytics Service
Provides system-wide statistics and analytics for administrators
"""

import json
from datetime import datetime, timedelta
from django.db.models import Count, Sum, Avg, Q, F
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.contrib.auth.models import User
from django.utils import timezone

from apps.users.models import UserProfile
from apps.doctors.models import Doctor, Appointment, Review
from apps.payments.models import Payment, Transaction


class AdminAnalytics:
    """
    Comprehensive admin analytics service for system-wide insights
    """
    
    def __init__(self):
        self.today = timezone.now().date()
        self.thirty_days_ago = self.today - timedelta(days=30)
        self.six_months_ago = self.today - timedelta(days=180)
        self.one_year_ago = self.today - timedelta(days=365)
    
    def get_system_overview(self):
        """Get high-level system statistics"""
        total_users = User.objects.count()
        total_doctors = Doctor.objects.count()
        total_patients = UserProfile.objects.count()
        total_appointments = Appointment.objects.count()
        
        # Active users (logged in within last 30 days)
        active_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        # Appointments this month
        appointments_this_month = Appointment.objects.filter(
            appointment_date__gte=self.thirty_days_ago
        ).count()
        
        # Total revenue (if payments exist)
        total_revenue = Payment.objects.filter(
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Average rating
        avg_rating = Review.objects.aggregate(
            avg=Avg('overall_rating')
        )['avg'] or 0
        
        return {
            'total_users': total_users,
            'total_doctors': total_doctors,
            'total_patients': total_patients,
            'total_appointments': total_appointments,
            'active_users': active_users,
            'appointments_this_month': appointments_this_month,
            'total_revenue': total_revenue,
            'average_rating': round(avg_rating, 1),
            'user_activity_rate': round((active_users / total_users) * 100, 1) if total_users > 0 else 0,
        }
    
    def get_user_growth_data(self):
        """Get user growth statistics over time"""
        user_growth = User.objects.filter(
            date_joined__gte=self.six_months_ago
        ).annotate(
            month=TruncMonth('date_joined')
        ).values('month').annotate(
            new_users=Count('id')
        ).order_by('month')
        
        doctor_growth = Doctor.objects.filter(
            user__date_joined__gte=self.six_months_ago
        ).annotate(
            month=TruncMonth('user__date_joined')
        ).values('month').annotate(
            new_doctors=Count('id')
        ).order_by('month')
        
        # Format for charts
        growth_data = []
        for entry in user_growth:
            month_str = entry['month'].strftime('%b %Y')
            doctor_count = next(
                (d['new_doctors'] for d in doctor_growth if d['month'] == entry['month']), 
                0
            )
            growth_data.append({
                'month': month_str,
                'users': entry['new_users'],
                'doctors': doctor_count,
                'patients': entry['new_users'] - doctor_count
            })
        
        return growth_data
    
    def get_appointment_analytics(self):
        """Get comprehensive appointment analytics"""
        # Appointment trends by month
        appointment_trends = Appointment.objects.filter(
            appointment_date__gte=self.six_months_ago
        ).annotate(
            month=TruncMonth('appointment_date')
        ).values('month').annotate(
            appointments=Count('id'),
            completed=Count('id', filter=Q(status='completed')),
            cancelled=Count('id', filter=Q(status='cancelled'))
        ).order_by('month')
        
        # Format for charts
        trends_data = []
        for entry in appointment_trends:
            trends_data.append({
                'month': entry['month'].strftime('%b %Y'),
                'appointments': entry['appointments'],
                'completed': entry['completed'],
                'cancelled': entry['cancelled'],
                'completion_rate': round((entry['completed'] / entry['appointments']) * 100, 1) if entry['appointments'] > 0 else 0
            })
        
        # Appointment status distribution
        status_distribution = Appointment.objects.values('status').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Popular appointment types
        appointment_types = Appointment.objects.values('appointment_type').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return {
            'trends': trends_data,
            'status_distribution': list(status_distribution),
            'appointment_types': list(appointment_types)
        }
    
    def get_revenue_analytics(self):
        """Get revenue and financial analytics"""
        # Revenue trends by month
        revenue_trends = Payment.objects.filter(
            status='completed',
            created_at__gte=self.six_months_ago
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            revenue=Sum('amount'),
            transactions=Count('id')
        ).order_by('month')
        
        trends_data = []
        for entry in revenue_trends:
            trends_data.append({
                'month': entry['month'].strftime('%b %Y'),
                'revenue': float(entry['revenue']),
                'transactions': entry['transactions'],
                'avg_transaction': round(float(entry['revenue']) / entry['transactions'], 2) if entry['transactions'] > 0 else 0
            })
        
        # Payment method distribution
        payment_methods = Payment.objects.filter(
            status='completed'
        ).values('payment_method').annotate(
            count=Count('id'),
            total_amount=Sum('amount')
        ).order_by('-total_amount')
        
        # Top earning doctors
        top_doctors = Doctor.objects.annotate(
            earnings=Sum('appointments__payments__amount', filter=Q(appointments__payments__status='completed'))
        ).order_by('-earnings')[:10]
        
        return {
            'trends': trends_data,
            'payment_methods': list(payment_methods),
            'top_doctors': [{
                'name': doctor.user.get_full_name(),
                'specialty': doctor.specialization,
                'earnings': float(doctor.earnings) if doctor.earnings else 0
            } for doctor in top_doctors if doctor.earnings]
        }
    
    def get_doctor_performance_metrics(self):
        """Get doctor performance analytics"""
        # Top rated doctors
        top_rated = Doctor.objects.annotate(
            avg_rating=Avg('reviews__overall_rating'),
            review_count=Count('reviews')
        ).filter(review_count__gte=5).order_by('-avg_rating')[:10]
        
        # Most active doctors
        most_active = Doctor.objects.annotate(
            appointment_count=Count('appointments')
        ).order_by('-appointment_count')[:10]
        
        # Specialty distribution
        specialty_stats = Doctor.objects.values('specialization').annotate(
            count=Count('id'),
            avg_rating=Avg('reviews__overall_rating'),
            total_appointments=Count('appointments')
        ).order_by('-count')
        
        return {
            'top_rated': [{
                'name': doc.user.get_full_name(),
                'specialty': doc.specialization,
                'rating': round(doc.avg_rating, 1) if doc.avg_rating else 0,
                'reviews': doc.review_count
            } for doc in top_rated],
            'most_active': [{
                'name': doc.user.get_full_name(),
                'specialty': doc.specialization,
                'appointments': doc.appointment_count
            } for doc in most_active],
            'specialty_stats': list(specialty_stats)
        }
    
    def get_system_health_metrics(self):
        """Get system health and performance metrics"""
        # Recent activity (last 7 days)
        week_ago = self.today - timedelta(days=7)
        
        daily_metrics = []
        for i in range(7):
            date = week_ago + timedelta(days=i)
            appointments_count = Appointment.objects.filter(appointment_date=date).count()
            new_users = User.objects.filter(date_joined__date=date).count()
            reviews_count = Review.objects.filter(created_at__date=date).count()
            
            daily_metrics.append({
                'date': date.strftime('%m/%d'),
                'appointments': appointments_count,
                'new_users': new_users,
                'reviews': reviews_count
            })
        
        # Error rates and issues (would need logging integration)
        failed_appointments = Appointment.objects.filter(
            status='cancelled',
            appointment_date__gte=week_ago
        ).count()
        
        total_recent_appointments = Appointment.objects.filter(
            appointment_date__gte=week_ago
        ).count()
        
        cancellation_rate = round(
            (failed_appointments / total_recent_appointments) * 100, 1
        ) if total_recent_appointments > 0 else 0
        
        return {
            'daily_activity': daily_metrics,
            'cancellation_rate': cancellation_rate,
            'system_uptime': 99.9,  # Would integrate with monitoring service
            'avg_response_time': 245,  # Would integrate with monitoring service
        }
    
    def get_geographic_distribution(self):
        """Get user geographic distribution"""
        # User distribution by city/state
        user_locations = UserProfile.objects.values('city', 'state').annotate(
            user_count=Count('id')
        ).order_by('-user_count')[:20]
        
        # Doctor distribution
        doctor_locations = Doctor.objects.values('city', 'state').annotate(
            doctor_count=Count('id')
        ).order_by('-doctor_count')[:20]
        
        return {
            'user_distribution': list(user_locations),
            'doctor_distribution': list(doctor_locations)
        }
    
    def get_comprehensive_report(self):
        """Get complete analytics report"""
        return {
            'system_overview': self.get_system_overview(),
            'user_growth': self.get_user_growth_data(),
            'appointment_analytics': self.get_appointment_analytics(),
            'revenue_analytics': self.get_revenue_analytics(),
            'doctor_performance': self.get_doctor_performance_metrics(),
            'system_health': self.get_system_health_metrics(),
            'geographic_distribution': self.get_geographic_distribution(),
            'generated_at': timezone.now().isoformat()
        }
    
    # JSON serialization methods for chart data
    def get_user_growth_json(self):
        return json.dumps(self.get_user_growth_data())
    
    def get_appointment_trends_json(self):
        return json.dumps(self.get_appointment_analytics()['trends'])
    
    def get_revenue_trends_json(self):
        return json.dumps(self.get_revenue_analytics()['trends'])
    
    def get_daily_activity_json(self):
        return json.dumps(self.get_system_health_metrics()['daily_activity'])


# Utility function for admin views
def get_admin_dashboard_context():
    """
    Get context data for admin dashboard template
    """
    analytics = AdminAnalytics()
    
    return {
        'system_overview': analytics.get_system_overview(),
        'user_growth': analytics.get_user_growth_data(),
        'appointment_analytics': analytics.get_appointment_analytics(),
        'revenue_analytics': analytics.get_revenue_analytics(),
        'doctor_performance': analytics.get_doctor_performance_metrics(),
        'system_health': analytics.get_system_health_metrics(),
        'geographic_distribution': analytics.get_geographic_distribution(),
        
        # JSON data for charts
        'user_growth_json': analytics.get_user_growth_json(),
        'appointment_trends_json': analytics.get_appointment_trends_json(),
        'revenue_trends_json': analytics.get_revenue_trends_json(),
        'daily_activity_json': analytics.get_daily_activity_json(),
    }
