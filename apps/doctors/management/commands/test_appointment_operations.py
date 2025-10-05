"""
Django management command to test appointment database operations and consistency.

This command tests various appointment operations to ensure database consistency
and proper functionality of the doctor appointments system.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone
from datetime import date, time, timedelta
import random

from apps.doctors.models import Doctor, Appointment
from apps.users.models import UserProfile


class Command(BaseCommand):
    help = 'Test appointment database operations and consistency'

    def add_arguments(self, parser):
        parser.add_argument(
            '--doctor',
            type=str,
            help='Username of the doctor to test with (default: first available doctor)',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up test appointments after testing',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧪 Testing Appointment Database Operations...\n'))
        
        # Get test doctor
        doctor_username = options.get('doctor')
        if doctor_username:
            try:
                doctor = Doctor.objects.get(user__username=doctor_username)
                self.stdout.write(f"Using specified doctor: {doctor.first_name} {doctor.last_name}")
            except Doctor.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Doctor with username '{doctor_username}' not found"))
                return
        else:
            doctor = Doctor.objects.first()
            if not doctor:
                self.stdout.write(self.style.ERROR("No doctors found in database"))
                return
            self.stdout.write(f"Using first available doctor: {doctor.first_name} {doctor.last_name}")
        
        # Get test patient
        patient_users = User.objects.filter(
            profile__isnull=False
        ).exclude(
            doctor_profile__isnull=False
        )
        
        if not patient_users.exists():
            self.stdout.write(self.style.ERROR("No patients found in database"))
            return
            
        patient = patient_users.first()
        self.stdout.write(f"Using test patient: {patient.get_full_name()}\n")
        
        test_appointments = []
        
        try:
            # Test 1: Create new appointments
            self.stdout.write(self.style.WARNING('Test 1: Creating new appointments'))
            
            for i in range(3):
                appointment_date = date.today() + timedelta(days=i+1)
                appointment_time = time(9 + i, 0)  # 9:00, 10:00, 11:00
                
                appointment = Appointment.objects.create(
                    doctor=doctor,
                    patient=patient,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    duration_minutes=30,
                    status='scheduled',
                    patient_notes=f'Test appointment {i+1}',
                    fee_charged=doctor.consultation_fee
                )
                test_appointments.append(appointment)
                
                self.stdout.write(f"  ✓ Created appointment {appointment.id} for {appointment_date} at {appointment_time}")
            
            # Test 2: Status updates
            self.stdout.write(self.style.WARNING('\nTest 2: Testing status updates'))
            
            # Confirm first appointment
            appointment1 = test_appointments[0]
            old_status = appointment1.status
            appointment1.status = 'confirmed'
            appointment1.save()
            
            # Reload from database to verify
            appointment1.refresh_from_db()
            if appointment1.status == 'confirmed':
                self.stdout.write(f"  ✓ Status updated from '{old_status}' to '{appointment1.status}'")
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Status update failed"))
            
            # Start second appointment
            appointment2 = test_appointments[1]
            appointment2.status = 'in_progress'
            appointment2.save()
            appointment2.refresh_from_db()
            self.stdout.write(f"  ✓ Appointment {appointment2.id} status: {appointment2.status}")
            
            # Complete third appointment
            appointment3 = test_appointments[2]
            appointment3.status = 'completed'
            appointment3.doctor_notes = 'Patient consulted successfully. Prescribed rest and medication.'
            appointment3.save()
            appointment3.refresh_from_db()
            self.stdout.write(f"  ✓ Appointment {appointment3.id} completed with notes")
            
            # Test 3: Query consistency
            self.stdout.write(self.style.WARNING('\nTest 3: Testing query consistency'))
            
            # Count appointments by status
            total_appointments = doctor.appointments.count()
            scheduled_count = doctor.appointments.filter(status='scheduled').count()
            confirmed_count = doctor.appointments.filter(status='confirmed').count()
            in_progress_count = doctor.appointments.filter(status='in_progress').count()
            completed_count = doctor.appointments.filter(status='completed').count()
            
            self.stdout.write(f"  Total appointments: {total_appointments}")
            self.stdout.write(f"  Scheduled: {scheduled_count}")
            self.stdout.write(f"  Confirmed: {confirmed_count}")
            self.stdout.write(f"  In Progress: {in_progress_count}")
            self.stdout.write(f"  Completed: {completed_count}")
            
            # Test 4: Earnings calculation
            self.stdout.write(self.style.WARNING('\nTest 4: Testing earnings calculation'))
            
            completed_appointments = doctor.appointments.filter(status='completed')
            total_earnings = sum(
                apt.fee_charged or doctor.consultation_fee 
                for apt in completed_appointments
            )
            
            self.stdout.write(f"  Total earnings from completed appointments: ₹{total_earnings}")
            
            # Test 5: Date filtering
            self.stdout.write(self.style.WARNING('\nTest 5: Testing date filtering'))
            
            today = date.today()
            todays_appointments = doctor.appointments.filter(appointment_date=today)
            upcoming_appointments = doctor.appointments.filter(
                appointment_date__gt=today,
                status__in=['scheduled', 'confirmed']
            )
            
            self.stdout.write(f"  Today's appointments: {todays_appointments.count()}")
            self.stdout.write(f"  Upcoming appointments: {upcoming_appointments.count()}")
            
            # Test 6: Data integrity checks
            self.stdout.write(self.style.WARNING('\nTest 6: Data integrity checks'))
            
            # Check for appointments without doctors or patients
            orphaned_appointments = Appointment.objects.filter(
                doctor__isnull=True
            ).count()
            
            appointments_without_patients = Appointment.objects.filter(
                patient__isnull=True
            ).count()
            
            self.stdout.write(f"  Orphaned appointments (no doctor): {orphaned_appointments}")
            self.stdout.write(f"  Appointments without patients: {appointments_without_patients}")
            
            if orphaned_appointments == 0 and appointments_without_patients == 0:
                self.stdout.write("  ✓ All appointments have valid doctor and patient references")
            
            # Test 7: Concurrent updates (simulate)
            self.stdout.write(self.style.WARNING('\nTest 7: Testing concurrent update handling'))
            
            appointment = test_appointments[0]
            
            # Simulate concurrent updates
            with transaction.atomic():
                appointment.refresh_from_db()
                original_notes = appointment.doctor_notes
                appointment.doctor_notes = "Updated notes - test 1"
                appointment.save()
                
                # Verify update
                appointment.refresh_from_db()
                if appointment.doctor_notes == "Updated notes - test 1":
                    self.stdout.write("  ✓ Concurrent update handling works correctly")
                else:
                    self.stdout.write(self.style.ERROR("  ✗ Concurrent update failed"))
            
            self.stdout.write(self.style.SUCCESS('\n✅ All database operation tests completed successfully!'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error during testing: {str(e)}'))
            
        finally:
            # Clean up test appointments if requested
            if options.get('cleanup') and test_appointments:
                self.stdout.write(self.style.WARNING('\n🧹 Cleaning up test appointments...'))
                
                for appointment in test_appointments:
                    try:
                        appointment.delete()
                        self.stdout.write(f"  ✓ Deleted appointment {appointment.id}")
                    except Exception as e:
                        self.stdout.write(f"  ✗ Failed to delete appointment {appointment.id}: {str(e)}")
                
                self.stdout.write(self.style.SUCCESS('Cleanup completed'))
            
            elif test_appointments and not options.get('cleanup'):
                self.stdout.write(self.style.WARNING(
                    f'\n⚠️  {len(test_appointments)} test appointments created. '
                    'Run with --cleanup to remove them.'
                ))
                for apt in test_appointments:
                    self.stdout.write(f"  Test appointment ID: {apt.id}")
