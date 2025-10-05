"""
Django management command to populate data for all doctors.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.doctors.models import Doctor, Appointment
from datetime import date, time, timedelta
import random


class Command(BaseCommand):
    help = 'Populate appointment data for all doctors'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Populating data for all doctors...\n'))
        
        doctors = Doctor.objects.all()
        
        # Get some patients
        patients = User.objects.filter(
            profile__isnull=False
        ).exclude(
            doctor_profile__isnull=False
        )
        
        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found in database"))
            return
            
        today = date.today()
        this_month_start = today.replace(day=1)
        
        for doctor in doctors:
            self.stdout.write(f"\n👨‍⚕️ Processing Dr. {doctor.first_name} {doctor.last_name}")
            
            # Check current appointments
            total_appointments = doctor.appointments.count()
            this_month_appointments = doctor.appointments.filter(
                appointment_date__gte=this_month_start
            ).count()
            completed_this_month = doctor.appointments.filter(
                status='completed',
                appointment_date__gte=this_month_start
            ).count()
            
            self.stdout.write(f"  Current appointments: {total_appointments}")
            self.stdout.write(f"  This month: {this_month_appointments}")
            self.stdout.write(f"  Completed this month: {completed_this_month}")
            
            # If doctor has very few appointments, create some
            if total_appointments < 5 or this_month_appointments < 2:
                self.stdout.write("  📅 Creating appointments...")
                
                appointments_to_create = max(5 - total_appointments, 3 - this_month_appointments)
                appointments_created = 0
                
                for i in range(appointments_to_create):
                    # Try different dates to avoid conflicts
                    for attempt in range(10):  # Try 10 different times
                        try:
                            if i < 2:  # This month appointments
                                appointment_date = this_month_start + timedelta(days=random.randint(1, 28))
                                if appointment_date > today:
                                    appointment_date = today - timedelta(days=random.randint(1, 10))
                            else:  # Other appointments
                                appointment_date = today - timedelta(days=random.randint(30, 90))
                            
                            appointment_time = time(
                                random.randint(9, 16), 
                                random.choice([0, 15, 30, 45])
                            )
                            
                            patient = random.choice(patients)
                            status = random.choice(['completed', 'confirmed', 'scheduled', 'completed'])
                            
                            # Check if this time slot is already taken
                            existing = doctor.appointments.filter(
                                appointment_date=appointment_date,
                                appointment_time=appointment_time
                            ).exists()
                            
                            if existing:
                                continue  # Try next attempt
                                
                            # Create appointment with future date first
                            future_date = today + timedelta(days=random.randint(1, 30))
                            
                            appointment = Appointment.objects.create(
                                doctor=doctor,
                                patient=patient,
                                appointment_date=future_date,
                                appointment_time=appointment_time,
                                duration_minutes=30,
                                status='scheduled',
                                patient_notes=f'Sample consultation for {doctor.specialty}',
                                fee_charged=doctor.consultation_fee
                            )
                            
                            # Update with actual date and status
                            Appointment.objects.filter(id=appointment.id).update(
                                appointment_date=appointment_date,
                                status=status,
                                doctor_notes='Consultation completed successfully.' if status == 'completed' else ''
                            )
                            
                            appointments_created += 1
                            break  # Success, move to next appointment
                            
                        except Exception as e:
                            continue  # Try next attempt
                
                self.stdout.write(f"  ✅ Created {appointments_created} appointments")
            
            # Calculate updated earnings
            completed_this_month = doctor.appointments.filter(
                status='completed',
                appointment_date__gte=this_month_start
            )
            this_month_earnings = sum(
                apt.fee_charged or doctor.consultation_fee 
                for apt in completed_this_month
            )
            
            total_completed = doctor.appointments.filter(status='completed')
            total_earnings = sum(
                apt.fee_charged or doctor.consultation_fee 
                for apt in total_completed
            )
            
            self.stdout.write(f"  💰 This month earnings: ₹{this_month_earnings}")
            self.stdout.write(f"  💰 Total earnings: ₹{total_earnings}")
        
        self.stdout.write(self.style.SUCCESS('\n✅ All doctors data populated successfully!'))
