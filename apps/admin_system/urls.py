"""
Admin System URLs
URL patterns for the powerful admin interface
"""

from django.urls import path
from . import views

app_name = 'admin_system'

urlpatterns = [
    # Main dashboard
    path('', views.admin_dashboard, name='dashboard'),
    
    # User management
    path('users/', views.UserManagementView.as_view(), name='user_management'),
    path('users/bulk-action/', views.bulk_user_action, name='bulk_user_action'),
    
    # Doctor management
    path('doctors/', views.DoctorManagementView.as_view(), name='doctor_management'),
    path('doctors/bulk-action/', views.bulk_doctor_action, name='bulk_doctor_action'),
    
    # Appointment management
    path('appointments/', views.AppointmentManagementView.as_view(), name='appointment_management'),
    
    # System Alerts
    path('alerts/', views.system_alerts_view, name='system_alerts'),
    path('alerts/<int:alert_id>/read/', views.mark_alert_read, name='mark_alert_read'),
    path('alerts/<int:alert_id>/resolve/', views.mark_alert_resolved, name='mark_alert_resolved'),
    
    # Analytics
    path('analytics/', views.analytics_view, name='analytics'),
    
    # Security Monitoring
    path('security/', views.security_monitoring_view, name='security'),
    path('security/export-activity-log/', views.export_activity_log, name='export_activity_log'),
    
    # Data export
    path('export/', views.export_data, name='export_data'),
    
    # User management CRUD operations
    path('users/<int:user_id>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:user_id>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('users/<int:user_id>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/add/', views.UserCreateView.as_view(), name='user_create'),
    
    # Doctor management CRUD operations
    path('doctors/<int:doctor_id>/', views.DoctorDetailView.as_view(), name='doctor_detail'),
    path('doctors/<int:doctor_id>/edit/', views.DoctorUpdateView.as_view(), name='doctor_edit'),
    path('doctors/<int:doctor_id>/delete/', views.DoctorDeleteView.as_view(), name='doctor_delete'),
    path('doctors/add/', views.DoctorCreateView.as_view(), name='doctor_create'),
    
    # Appointment details and actions
    path('appointments/<int:appointment_id>/', views.AppointmentDetailView.as_view(), name='appointment_detail'),
    path('appointments/<int:appointment_id>/update-status/', views.update_appointment_status, name='update_appointment_status'),
]
