"""
Django management command to debug appointments view issues.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.doctors.models import Doctor, Appointment


class Command(BaseCommand):
    help = 'Debug appointments view issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 Debugging appointments view...\n'))
        
        try:
            # Check Dr. Vihaan Kapoor's appointments
            user = User.objects.get(username='dr.vihaan')
            self.stdout.write(f"User: {user.username} ({user.get_full_name()})")
            self.stdout.write(f"Has doctor_profile: {hasattr(user, 'doctor_profile')}")
            
            if hasattr(user, 'doctor_profile'):
                doctor = user.doctor_profile
                self.stdout.write(f"Doctor: Dr. {doctor.first_name} {doctor.last_name}")
                
                appointments = doctor.appointments.select_related('patient', 'patient__profile', 'doctor').all()
                self.stdout.write(f"Total appointments: {appointments.count()}")
                
                if appointments.exists():
                    self.stdout.write("\nFirst 5 appointments:")
                    for apt in appointments[:5]:
                        self.stdout.write(f"  ID {apt.id}: {apt.patient.get_full_name()} on {apt.appointment_date} at {apt.appointment_time} - {apt.status}")
                        self.stdout.write(f"    Patient profile exists: {hasattr(apt.patient, 'profile')}")
                        if hasattr(apt.patient, 'profile'):
                            self.stdout.write(f"    Profile phone: {apt.patient.profile.phone}")
                
                # Check if the view query would work
                queryset = Appointment.objects.select_related('patient', 'patient__profile', 'doctor').filter(doctor=doctor)
                self.stdout.write(f"\nView queryset count: {queryset.count()}")
                
                # Test the exact query from the view
                ordered_queryset = queryset.order_by('-appointment_date', '-appointment_time')
                self.stdout.write(f"Ordered queryset count: {ordered_queryset.count()}")
                
                if ordered_queryset.exists():
                    self.stdout.write("\nFirst appointment from ordered queryset:")
                    first_apt = ordered_queryset.first()
                    self.stdout.write(f"  {first_apt.id}: {first_apt.patient.get_full_name()} on {first_apt.appointment_date}")
                
            else:
                self.stdout.write(self.style.ERROR("User doesn't have doctor_profile"))
                
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR("User 'vihaan_doctor' not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
