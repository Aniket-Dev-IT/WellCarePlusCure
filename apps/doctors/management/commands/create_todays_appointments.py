"""
Django management command to create today's appointments for a doctor.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.doctors.models import Doctor, Appointment
from datetime import date, time
import random


class Command(BaseCommand):
    help = 'Create today\'s appointments for a specific doctor'

    def add_arguments(self, parser):
        parser.add_argument(
            '--doctor',
            type=str,
            help='Username of the doctor (default: dr.taylor)',
            default='dr.taylor'
        )

    def handle(self, *args, **options):
        doctor_username = options['doctor']
        self.stdout.write(self.style.SUCCESS(f'🔧 Creating today\'s appointments for {doctor_username}...\n'))
        
        try:
            # Get doctor
            user = User.objects.get(username=doctor_username)
            doctor = user.doctor_profile
            self.stdout.write(f"Doctor: Dr. {doctor.first_name} {doctor.last_name}")
            self.stdout.write(f"Consultation Fee: ₹{doctor.consultation_fee}")
            
            # Get some patients
            patients = User.objects.filter(
                profile__isnull=False
            ).exclude(
                doctor_profile__isnull=False
            )[:5]  # Get first 5 patients
            
            if not patients.exists():
                self.stdout.write(self.style.ERROR("No patients found in database"))
                return
            
            today = date.today()
            self.stdout.write(f"Creating appointments for today: {today}")
            
            # Check existing today's appointments
            existing_today = doctor.appointments.filter(appointment_date=today).count()
            self.stdout.write(f"Existing appointments today: {existing_today}")
            
            # Define appointment times for today
            appointment_times = [
                time(9, 0),   # 9:00 AM
                time(11, 0),  # 11:00 AM
                time(14, 0),  # 2:00 PM
                time(16, 0),  # 4:00 PM
            ]
            
            statuses = ['scheduled', 'confirmed', 'in_progress', 'completed']
            appointments_created = 0
            
            for i, appointment_time in enumerate(appointment_times):
                try:
                    # Check if this time slot is already taken
                    existing = doctor.appointments.filter(
                        appointment_date=today,
                        appointment_time=appointment_time
                    ).exists()
                    
                    if existing:
                        self.stdout.write(f"  ⏭️  Skipping {appointment_time} - already booked")
                        continue
                    
                    patient = random.choice(patients)
                    status = statuses[i % len(statuses)]
                    
                    appointment = Appointment.objects.create(
                        doctor=doctor,
                        patient=patient,
                        appointment_date=today,
                        appointment_time=appointment_time,
                        duration_minutes=30,
                        status=status,
                        patient_notes=f'Today\'s {status} appointment',
                        fee_charged=doctor.consultation_fee,
                        doctor_notes='Consultation completed successfully.' if status == 'completed' else 
                                   'Consultation in progress.' if status == 'in_progress' else ''
                    )
                    
                    appointments_created += 1
                    self.stdout.write(f"  ✓ Created appointment {appointment.id}: {patient.get_full_name()} at {appointment_time} ({status})")
                    
                except Exception as e:
                    self.stdout.write(f"  ✗ Failed to create appointment at {appointment_time}: {str(e)}")
            
            # Calculate updated statistics
            self.stdout.write(self.style.WARNING('\n📊 Updated Today\'s Statistics:'))
            
            todays_appointments = doctor.appointments.filter(appointment_date=today)
            todays_total = todays_appointments.count()
            todays_confirmed = todays_appointments.filter(
                status__in=['confirmed', 'scheduled']
            ).count()
            todays_completed = todays_appointments.filter(status='completed').count()
            todays_in_progress = todays_appointments.filter(status='in_progress').count()
            
            # Calculate today's earnings
            todays_earnings = sum(
                apt.fee_charged or doctor.consultation_fee 
                for apt in todays_appointments.filter(status='completed')
            )
            
            self.stdout.write(f"Total Today: {todays_total}")
            self.stdout.write(f"Confirmed Today: {todays_confirmed}")
            self.stdout.write(f"Completed Today: {todays_completed}")
            self.stdout.write(f"In Progress Today: {todays_in_progress}")
            self.stdout.write(f"Today's Earnings: ₹{todays_earnings}")
            
            self.stdout.write(self.style.SUCCESS(f'\n✅ Created {appointments_created} appointments for today!'))
            
            if appointments_created > 0:
                self.stdout.write(self.style.WARNING('\n🔄 Please refresh the appointments page to see the updated data.'))
            
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User '{doctor_username}' not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
