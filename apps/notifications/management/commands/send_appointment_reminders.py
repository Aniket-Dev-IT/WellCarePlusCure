from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from apps.notifications.signals import send_appointment_reminders
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send appointment reminders for upcoming appointments'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=1,
            help='Number of days ahead to send reminders (default: 1)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually sending reminders'
        )
    
    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Sending appointment reminders for appointments {days_ahead} days ahead (dry_run: {dry_run})'
            )
        )
        
        # Import models here to avoid circular imports
        try:
            from apps.users.models import Appointment
        except ImportError:
            self.stdout.write(
                self.style.ERROR('Appointment model not found. Please check your app configuration.')
            )
            return
        
        # Get appointments for the target date
        target_date = timezone.now().date() + timedelta(days=days_ahead)
        upcoming_appointments = Appointment.objects.filter(
            date=target_date,
            status__in=['scheduled', 'confirmed']
        ).select_related('patient', 'doctor__user')
        
        appointment_count = upcoming_appointments.count()
        
        self.stdout.write(
            f'Found {appointment_count} appointments for {target_date}'
        )
        
        if dry_run:
            if appointment_count > 0:
                self.stdout.write('\\nAppointments that would receive reminders:')
                for appointment in upcoming_appointments[:10]:  # Show first 10
                    self.stdout.write(
                        f'  - {appointment.patient.get_full_name()} with '
                        f'Dr. {appointment.doctor.user.get_full_name()} at {appointment.time}'
                    )
                if appointment_count > 10:
                    self.stdout.write(f'  ... and {appointment_count - 10} more')
            return
        
        if appointment_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No appointments found for reminder sending.')
            )
            return
        
        # Send reminders
        try:
            reminder_count = send_appointment_reminders()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully sent {reminder_count} appointment reminders'
                )
            )
            
            if reminder_count < appointment_count * 2:  # Each appointment should send 2 reminders (patient + doctor)
                self.stdout.write(
                    self.style.WARNING(
                        f'Expected to send {appointment_count * 2} reminders but only sent {reminder_count}. '
                        'Some reminders may have failed.'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error sending appointment reminders: {str(e)}')
            )
            logger.error(f'Appointment reminder error: {str(e)}')
            raise
