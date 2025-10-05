from django.contrib import admin
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.contrib.auth.models import User
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        'profile_thumbnail', 'user_info', 'age_group', 'contact_info', 
        'location_info', 'medical_summary', 'insurance_status', 
        'notification_preferences', 'account_status', 'created_at'
    ]
    list_filter = [
        'gender', 'blood_group', 'city', 'state', 'country',
        'email_notifications', 'sms_notifications', 'is_phone_verified', 
        'is_email_verified', 'created_at', 'updated_at'
    ]
    search_fields = [
        'user__username', 'user__first_name', 'user__last_name', 
        'user__email', 'phone', 'alternate_phone', 
        'emergency_contact_name', 'emergency_contact_phone'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'age', 'profile_picture_preview',
        'health_summary', 'appointment_history', 'profile_completion_status'
    ]
    list_select_related = ['user']
    list_per_page = 25
    
    fieldsets = (
        ('Profile Picture', {
            'fields': ('profile_picture_preview',),
            'classes': ('wide',)
        }),
        ('User Information', {
            'fields': ('user',)
        }),
        ('Personal Details', {
            'fields': (
                'date_of_birth', 'age', 'gender', 
                'phone', 'alternate_phone'
            )
        }),
        ('Address Information', {
            'fields': (
                'address_line1', 'address_line2', 
                'city', 'state', 'postal_code', 'country'
            )
        }),
        ('Medical Information', {
            'fields': (
                'blood_group', 'allergies', 'chronic_conditions', 
                'medications'
            )
        }),
        ('Insurance & Additional Info', {
            'fields': (
                'insurance_provider', 'insurance_number', 'occupation'
            ),
            'classes': ('collapse',)
        }),
        ('Emergency Contact', {
            'fields': (
                'emergency_contact_name', 'emergency_contact_phone', 
                'emergency_contact_relation'
            ),
            'classes': ('collapse',)
        }),
        ('Preferences & Media', {
            'fields': (
                'profile_picture', 'email_notifications', 
                'sms_notifications', 'is_phone_verified', 'is_email_verified'
            )
        }),
        ('Health & Activity Summary', {
            'fields': (
                'health_summary', 'appointment_history', 
                'profile_completion_status'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def profile_thumbnail(self, obj):
        """Display profile picture thumbnail"""
        return format_html(
            '<img src="{}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover;" />',
            obj.profile_picture_url
        )
        return format_html(
            '<div style="width: 40px; height: 40px; border-radius: 50%; background: #17a2b8; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">{}</div>',
            (obj.user.first_name[:1] + obj.user.last_name[:1]) if obj.user.first_name and obj.user.last_name else 'U'
        )
    profile_thumbnail.short_description = 'Photo'
    
    def profile_picture_preview(self, obj):
        """Display larger profile picture preview"""
        return format_html(
            '<img src="{}" style="max-width: 200px; max-height: 200px; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);" />',
            obj.profile_picture_url
        )
    profile_picture_preview.short_description = 'Profile Picture Preview'
    
    def user_info(self, obj):
        """Display user information with status indicators"""
        name = obj.user.get_full_name() or obj.user.username
        status_indicators = []
        
        if obj.user.is_staff:
            status_indicators.append('<span style="background: #6c757d; color: white; padding: 1px 4px; border-radius: 3px; font-size: 9px;">STAFF</span>')
        if obj.user.is_superuser:
            status_indicators.append('<span style="background: #dc3545; color: white; padding: 1px 4px; border-radius: 3px; font-size: 9px;">ADMIN</span>')
        if not obj.user.is_active:
            status_indicators.append('<span style="background: #ffc107; color: black; padding: 1px 4px; border-radius: 3px; font-size: 9px;">INACTIVE</span>')
        
        status_html = ' '.join(status_indicators)
        
        return format_html(
            '<div><strong>{}</strong><br/><small>{}</small><br/>{}</div>',
            name, obj.user.email, status_html
        )
    user_info.short_description = 'User'
    user_info.admin_order_field = 'user__first_name'
    
    def age_group(self, obj):
        """Display age with age group indicator"""
        if obj.age:
            age = obj.age
            if age < 18:
                group = 'Minor'
                color = '#17a2b8'
            elif age < 30:
                group = 'Young Adult'
                color = '#28a745'
            elif age < 50:
                group = 'Adult'
                color = '#ffc107'
            elif age < 65:
                group = 'Middle-aged'
                color = '#fd7e14'
            else:
                group = 'Senior'
                color = '#6f42c1'
            
            return format_html(
                '<div><strong>{} yrs</strong><br/><small style="color: {}; font-weight: bold;">{}</small></div>',
                age, color, group
            )
        return '-'
    age_group.short_description = 'Age Group'
    age_group.admin_order_field = 'date_of_birth'
    
    def contact_info(self, obj):
        """Display contact information"""
        contact_html = '<div style="font-size: 11px;">'
        if obj.phone:
            contact_html += f'📱 {obj.phone}<br/>'
        if obj.alternate_phone:
            contact_html += f'📞 {obj.alternate_phone}<br/>'
        contact_html += '</div>'
        return format_html(contact_html) if obj.phone else '-'
    contact_info.short_description = 'Contact'
    
    def location_info(self, obj):
        """Display location with country flag"""
        if obj.city and obj.state:
            flag = '🇮🇳' if obj.country == 'India' else '🌍'
            return format_html(
                '<div style="font-size: 11px;">{} {}<br/>{}</div>',
                flag, obj.city, obj.state
            )
        return '-'
    location_info.short_description = 'Location'
    
    def medical_summary(self, obj):
        """Display medical information summary"""
        medical_info = []
        if obj.blood_group:
            colors = {
                'A+': '#e74c3c', 'A-': '#c0392b', 'B+': '#3498db', 'B-': '#2980b9',
                'AB+': '#9b59b6', 'AB-': '#8e44ad', 'O+': '#e67e22', 'O-': '#d35400'
            }
            color = colors.get(obj.blood_group, '#95a5a6')
            medical_info.append(f'<span style="background: {color}; color: white; padding: 2px 5px; border-radius: 8px; font-size: 10px; font-weight: bold;">{obj.blood_group}</span>')
        
        if obj.allergies:
            medical_info.append('<span style="background: #f39c12; color: white; padding: 1px 4px; border-radius: 6px; font-size: 9px;">🚨 ALLERGIES</span>')
        
        if obj.chronic_conditions:
            medical_info.append('<span style="background: #e74c3c; color: white; padding: 1px 4px; border-radius: 6px; font-size: 9px;">⚕️ CONDITIONS</span>')
        
        return format_html('<div>{}</div>', '<br/>'.join(medical_info)) if medical_info else '-'
    medical_summary.short_description = 'Medical Info'
    
    def insurance_status(self, obj):
        """Display insurance status"""
        if obj.insurance_provider:
            return format_html(
                '<span style="color: #28a745; font-weight: bold;">✓ Insured</span><br/><small style="font-size: 9px;">{}</small>',
                obj.insurance_provider
            )
        return format_html('<span style="color: #dc3545;">✗ No Insurance</span>')
    insurance_status.short_description = 'Insurance'
    insurance_status.admin_order_field = 'insurance_provider'
    
    def notification_preferences(self, obj):
        """Display notification preferences"""
        prefs = []
        if obj.email_notifications:
            prefs.append('📧')
        if obj.sms_notifications:
            prefs.append('📱')
        
        return format_html('<div style="font-size: 16px;">{}</div>', ' '.join(prefs)) if prefs else '🔇'
    notification_preferences.short_description = 'Notifications'
    
    def account_status(self, obj):
        """Display account status indicators"""
        status_html = '<div style="font-size: 11px;">'
        if obj.user.is_active:
            status_html += '<span style="color: #28a745; font-weight: bold;">● Active</span><br/>'
        else:
            status_html += '<span style="color: #dc3545; font-weight: bold;">● Inactive</span><br/>'
        
        if obj.is_phone_verified and obj.is_email_verified:
            status_html += '<span style="color: #17a2b8;">✓ Verified</span>'
        elif obj.is_phone_verified or obj.is_email_verified:
            status_html += '<span style="color: #ffc107;">⚠ Partial Verified</span>'
        else:
            status_html += '<span style="color: #ffc107;">⚠ Unverified</span>'
        
        status_html += '</div>'
        return format_html(status_html)
    account_status.short_description = 'Status'
    
    def health_summary(self, obj):
        """Display comprehensive health summary"""
        try:
            from apps.doctors.models import Appointment
            appointments = Appointment.objects.filter(patient=obj.user)
            total_appointments = appointments.count()
            completed_appointments = appointments.filter(status='completed').count()
            
            # BMI calculation not available without height/weight fields
            
            return format_html(
                '''
                <div style="background: #f8f9fa; padding: 10px; border-radius: 6px; font-size: 12px;">
                    <strong>🏥 Health Summary</strong><br/>
                    • Total Appointments: {}<br/>
                    • Completed: {}<br/>
                    • Blood Group: {}<br/>
                    • Insurance: {}
                </div>
                ''',
                total_appointments,
                completed_appointments,
                obj.blood_group or 'Not specified',
                obj.insurance_provider or 'Not specified'
            )
        except:
            return "Health summary not available"
    health_summary.short_description = 'Health Summary'
    
    def appointment_history(self, obj):
        """Display recent appointment history"""
        try:
            from apps.doctors.models import Appointment
            recent_appointments = Appointment.objects.filter(
                patient=obj.user
            ).order_by('-appointment_date')[:3]
            
            if not recent_appointments:
                return "No appointments yet"
            
            history_html = "<div style='font-size: 11px;'><strong>Recent Appointments:</strong><br/>"
            for apt in recent_appointments:
                history_html += f"• {apt.appointment_date} - Dr. {apt.doctor.display_name}<br/>"
            history_html += "</div>"
            
            return format_html(history_html)
        except:
            return "Unable to load appointment history"
    appointment_history.short_description = 'Recent Appointments'
    
    def profile_completion_status(self, obj):
        """Display profile completion percentage"""
        fields = [
            obj.profile_picture, obj.phone, obj.date_of_birth,
            obj.address_line1, obj.city, obj.state, obj.blood_group,
            obj.emergency_contact_name, obj.emergency_contact_phone
        ]
        completed = sum(1 for field in fields if field)
        percentage = (completed / len(fields)) * 100
        
        if percentage >= 80:
            color = '#28a745'
        elif percentage >= 60:
            color = '#ffc107'
        else:
            color = '#dc3545'
        
        return format_html(
            '<div style="width: 100px; background: #e9ecef; border-radius: 10px; padding: 2px;"><div style="width: {}%; background: {}; height: 8px; border-radius: 8px;"></div></div><small>{:.0f}% Complete</small>',
            percentage, color, percentage
        )
    profile_completion_status.short_description = 'Profile Completion'
    
    actions = ['mark_as_verified', 'mark_as_unverified', 'enable_notifications', 'disable_notifications']
    
    def mark_as_verified(self, request, queryset):
        updated = queryset.update(is_phone_verified=True, is_email_verified=True)
        self.message_user(request, f'{updated} user profiles marked as verified.')
    mark_as_verified.short_description = "Mark selected profiles as verified"
    
    def mark_as_unverified(self, request, queryset):
        updated = queryset.update(is_phone_verified=False, is_email_verified=False)
        self.message_user(request, f'{updated} user profiles marked as unverified.')
    mark_as_unverified.short_description = "Mark selected profiles as unverified"
    
    def enable_notifications(self, request, queryset):
        updated = queryset.update(email_notifications=True, sms_notifications=True)
        self.message_user(request, f'Enabled notifications for {updated} user profiles.')
    enable_notifications.short_description = "Enable all notifications"
    
    def disable_notifications(self, request, queryset):
        updated = queryset.update(email_notifications=False, sms_notifications=False)
        self.message_user(request, f'Disabled notifications for {updated} user profiles.')
    disable_notifications.short_description = "Disable all notifications"
