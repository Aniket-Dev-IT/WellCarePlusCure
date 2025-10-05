"""
Django management command to send appointment reminders.

This command should be run daily (usually via cron job) to send
reminder emails to patients with appointments the next day.

Usage:
    python manage.py send_appointment_reminders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.users.email_utils import send_bulk_reminders
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send appointment reminder emails to patients with appointments tomorrow'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview emails that would be sent without actually sending them',
        )
        
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=1,
            help='Number of days ahead to send reminders (default: 1)',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        dry_run = options['dry_run']
        days_ahead = options['days_ahead']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'🔔 Starting appointment reminder process...'
            )
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('📋 DRY RUN MODE - No emails will be sent')
            )
        
        try:
            from apps.doctors.models import Appointment
            
            # Calculate target date
            target_date = timezone.now().date() + timedelta(days=days_ahead)
            
            # Get appointments that need reminders
            appointments = Appointment.objects.filter(
                appointment_date=target_date,
                status__in=['scheduled', 'confirmed']
            ).select_related('patient', 'doctor')
            
            total_appointments = appointments.count()
            
            self.stdout.write(
                f'📅 Found {total_appointments} appointments for {target_date.strftime("%B %d, %Y")}'
            )
            
            if total_appointments == 0:
                self.stdout.write(
                    self.style.SUCCESS('✅ No reminders to send today.')
                )
                return
            
            # Display appointments that will receive reminders
            self.stdout.write('\n📋 Appointments to remind:')
            self.stdout.write('-' * 60)
            
            for appointment in appointments[:10]:  # Show first 10
                patient_name = appointment.patient.get_full_name() or appointment.patient.username
                doctor_name = appointment.doctor.display_name
                time_str = appointment.appointment_time.strftime('%I:%M %p')
                
                self.stdout.write(
                    f'👤 {patient_name} → 👨‍⚕️ {doctor_name} at {time_str}'
                )
            
            if total_appointments > 10:
                self.stdout.write(f'... and {total_appointments - 10} more')
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING('\n📋 DRY RUN: No emails were sent')
                )
                return
            
            # Send the reminders
            self.stdout.write(f'\n📧 Sending {total_appointments} reminder emails...')
            
            summary = send_bulk_reminders()
            
            # Display results
            self.stdout.write('\n📊 Results:')
            self.stdout.write('-' * 30)
            self.stdout.write(f'Total appointments: {summary["total_appointments"]}')
            self.stdout.write(
                self.style.SUCCESS(f'✅ Emails sent successfully: {summary["emails_sent"]}')
            )
            
            if summary['errors'] > 0:
                self.stdout.write(
                    self.style.ERROR(f'❌ Failed to send: {summary["errors"]}')
                )
            
            # Calculate success rate
            if summary['total_appointments'] > 0:
                success_rate = (summary['emails_sent'] / summary['total_appointments']) * 100
                self.stdout.write(f'📈 Success rate: {success_rate:.1f}%')
            
            if summary['emails_sent'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n🎉 Successfully sent {summary["emails_sent"]} appointment reminder emails!'
                    )
                )
            
            # Log the results
            logger.info(f'Appointment reminders sent: {summary}')
            
        except Exception as e:
            error_msg = f'❌ Error sending appointment reminders: {str(e)}'
            self.stdout.write(self.style.ERROR(error_msg))
            logger.error(error_msg, exc_info=True)
            raise
    
    def get_appointment_summary(self, appointments):
        """Get a summary of appointments by doctor and time."""
        summary = {}
        
        for appointment in appointments:
            doctor_name = appointment.doctor.display_name
            time_slot = appointment.appointment_time.strftime('%I:%M %p')
            
            if doctor_name not in summary:
                summary[doctor_name] = []
            
            summary[doctor_name].append({
                'patient': appointment.patient.get_full_name() or appointment.patient.username,
                'time': time_slot
            })
        
        return summary
