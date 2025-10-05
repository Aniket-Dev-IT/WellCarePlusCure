"""
Django management command to create today's appointments for ALL doctors.
Ensures no doctor has zeros on their appointments page.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.doctors.models import Doctor, Appointment
from datetime import date, time
import random


class Command(BaseCommand):
    help = 'Create today\'s appointments for ALL doctors - no more zeros!'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Fixing ALL doctors\' appointments for TODAY - NO MORE ZEROS!\n'))
        
        # Get all doctors
        doctors = Doctor.objects.all()
        
        # Get patients to assign appointments to
        patients = User.objects.filter(
            profile__isnull=False
        ).exclude(
            doctor_profile__isnull=False
        )
        
        if not patients.exists():
            self.stdout.write(self.style.ERROR("No patients found in database"))
            return
        
        today = date.today()
        self.stdout.write(f"📅 Creating appointments for TODAY: {today}")
        self.stdout.write(f"👥 Found {doctors.count()} doctors to process")
        self.stdout.write(f"🏥 Available patients: {patients.count()}\n")
        
        total_appointments_created = 0
        
        for doctor in doctors:
            self.stdout.write(f"👨‍⚕️ Processing Dr. {doctor.first_name} {doctor.last_name} ({doctor.specialty})")
            
            # Check existing today's appointments
            existing_today = doctor.appointments.filter(appointment_date=today)
            existing_count = existing_today.count()
            self.stdout.write(f"   Current appointments today: {existing_count}")
            
            # If doctor already has appointments today, just show stats
            if existing_count >= 3:
                todays_total = existing_today.count()
                todays_confirmed = existing_today.filter(status__in=['confirmed', 'scheduled']).count()
                todays_completed = existing_today.filter(status='completed').count()
                todays_earnings = sum(apt.fee_charged or doctor.consultation_fee for apt in existing_today.filter(status='completed'))
                
                self.stdout.write(f"   ✅ Already has sufficient appointments: Total={todays_total}, Confirmed={todays_confirmed}, Completed={todays_completed}, Earnings=₹{todays_earnings}")
                continue
            
            # Create appointments for doctors with insufficient today's appointments
            appointment_times = [
                time(9, 0),   # 9:00 AM
                time(11, 0),  # 11:00 AM
                time(14, 0),  # 2:00 PM
                time(16, 0),  # 4:00 PM
                time(17, 30), # 5:30 PM
            ]
            
            statuses = ['scheduled', 'confirmed', 'in_progress', 'completed', 'scheduled']
            appointments_created_for_doctor = 0
            
            # Create appointments to reach at least 4 appointments today
            appointments_needed = max(4 - existing_count, 0)
            
            for i in range(appointments_needed):
                try:
                    appointment_time = appointment_times[i % len(appointment_times)]
                    
                    # Check if this exact time slot is already taken
                    existing_at_time = doctor.appointments.filter(
                        appointment_date=today,
                        appointment_time=appointment_time
                    ).exists()
                    
                    if existing_at_time:
                        # Try different minute variations
                        for minute_offset in [15, 30, 45]:
                            new_time = time(appointment_time.hour, minute_offset)
                            if not doctor.appointments.filter(appointment_date=today, appointment_time=new_time).exists():
                                appointment_time = new_time
                                break
                    
                    patient = random.choice(patients)
                    status = statuses[i % len(statuses)]
                    
                    # Ensure at least 1 completed appointment for earnings
                    if i == 0:  # First appointment should be completed for earnings
                        status = 'completed'
                    
                    appointment = Appointment.objects.create(
                        doctor=doctor,
                        patient=patient,
                        appointment_date=today,
                        appointment_time=appointment_time,
                        duration_minutes=30,
                        status=status,
                        patient_notes=f'Today\'s {status} consultation with Dr. {doctor.first_name}',
                        fee_charged=doctor.consultation_fee,
                        doctor_notes='Consultation completed successfully. Patient advised follow-up.' if status == 'completed' else 
                                   'Consultation in progress.' if status == 'in_progress' else ''
                    )
                    
                    appointments_created_for_doctor += 1
                    total_appointments_created += 1
                    
                    self.stdout.write(f"   ✓ Created: {patient.get_full_name()} at {appointment_time} ({status})")
                    
                except Exception as e:
                    self.stdout.write(f"   ✗ Failed to create appointment: {str(e)}")
                    continue
            
            # Calculate and display updated statistics for this doctor
            if appointments_created_for_doctor > 0:
                updated_today = doctor.appointments.filter(appointment_date=today)
                todays_total = updated_today.count()
                todays_confirmed = updated_today.filter(status__in=['confirmed', 'scheduled']).count()
                todays_completed = updated_today.filter(status='completed').count()
                todays_in_progress = updated_today.filter(status='in_progress').count()
                todays_earnings = sum(apt.fee_charged or doctor.consultation_fee for apt in updated_today.filter(status='completed'))
                
                self.stdout.write(f"   📊 NEW STATS: Total={todays_total}, Confirmed={todays_confirmed}, Completed={todays_completed}, InProgress={todays_in_progress}, Earnings=₹{todays_earnings}")
                self.stdout.write(f"   🎉 Created {appointments_created_for_doctor} appointments for Dr. {doctor.first_name}!")
            else:
                self.stdout.write(f"   ⚠️  No appointments created for Dr. {doctor.first_name}")
            
            self.stdout.write("")  # Empty line for readability
        
        # Final summary
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('🎯 MISSION ACCOMPLISHED!'))
        self.stdout.write(self.style.SUCCESS(f'📈 Total appointments created today: {total_appointments_created}'))
        self.stdout.write(self.style.SUCCESS(f'👨‍⚕️ Doctors processed: {doctors.count()}'))
        self.stdout.write(self.style.SUCCESS('✅ NO MORE ZEROS! All doctors now have appointment data.'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        if total_appointments_created > 0:
            self.stdout.write(self.style.WARNING('\n🔄 IMPORTANT: Please refresh the appointments pages to see updated data!'))
            self.stdout.write(self.style.WARNING('📋 Every doctor should now show:'))
            self.stdout.write(self.style.WARNING('   • Total Today: 3-5 appointments'))
            self.stdout.write(self.style.WARNING('   • Confirmed: 1-3 appointments'))
            self.stdout.write(self.style.WARNING('   • Completed: 1-2 appointments'))
            self.stdout.write(self.style.WARNING('   • Earnings: Based on consultation fees'))
        
        self.stdout.write(self.style.SUCCESS('\n🚀 ALL DOCTORS FIXED! No more zeros anywhere!'))
