"""
Django management command to populate realistic doctor availability schedules.

This command creates comprehensive availability schedules for all doctors
based on their specialty, including both regular and emergency hours.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.doctors.models import Doctor, DoctorAvailability
from datetime import time
import random


class Command(BaseCommand):
    help = 'Populate realistic availability schedules for all doctors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing availability schedules before creating new ones',
        )
        parser.add_argument(
            '--doctor-id',
            type=int,
            help='Populate availability for a specific doctor ID only',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🏥 Populating doctor availability schedules...\n'))
        
        # Clear existing data if requested
        if options['clear_existing']:
            self.stdout.write('🗑️  Clearing existing availability schedules...')
            DoctorAvailability.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Cleared existing schedules\n'))
        
        # Get doctors to process
        if options['doctor_id']:
            doctors = Doctor.objects.filter(id=options['doctor_id'])
            if not doctors.exists():
                self.stdout.write(self.style.ERROR(f'❌ Doctor with ID {options["doctor_id"]} not found'))
                return
        else:
            doctors = Doctor.objects.all()
        
        self.stdout.write(f'👩‍⚕️ Processing {doctors.count()} doctors...\n')
        
        # Define availability templates based on specialty
        availability_templates = self.get_availability_templates()
        
        # Track statistics
        total_created = 0
        doctors_updated = 0
        
        for doctor in doctors:
            try:
                created_count = self.create_availability_for_doctor(doctor, availability_templates)
                if created_count > 0:
                    doctors_updated += 1
                    total_created += created_count
                    self.stdout.write(
                        f'✅ Dr. {doctor.first_name} {doctor.last_name} ({doctor.get_specialty_display()}): '
                        f'{created_count} availability slots'
                    )
                else:
                    self.stdout.write(
                        f'ℹ️  Dr. {doctor.first_name} {doctor.last_name}: Already has availability'
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error processing Dr. {doctor.first_name} {doctor.last_name}: {str(e)}')
                )
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Summary:')
        )
        self.stdout.write(f'   👥 Doctors processed: {doctors_updated}/{doctors.count()}')
        self.stdout.write(f'   📅 Total availability slots created: {total_created}')
        self.stdout.write(f'   🔄 You can now refresh the doctor profile pages to see the schedules!')

    def get_availability_templates(self):
        """Define availability templates for different medical specialties."""
        
        return {
            # General Medicine - Regular family doctor hours
            'general': [
                {'day': 0, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Monday
                {'day': 1, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Tuesday
                {'day': 2, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Wednesday
                {'day': 3, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Thursday
                {'day': 4, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Friday
                {'day': 5, 'start': time(9, 0), 'end': time(13, 0), 'type': 'regular'},   # Saturday
            ],
            
            # Cardiology - Specialist hours with emergency availability
            'cardiology': [
                {'day': 0, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Monday
                {'day': 1, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Tuesday
                {'day': 2, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Wednesday
                {'day': 3, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Thursday
                {'day': 4, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Friday
                {'day': 6, 'start': time(8, 0), 'end': time(12, 0), 'type': 'emergency'}, # Sunday emergency
            ],
            
            # Dermatology - Regular specialist schedule
            'dermatology': [
                {'day': 0, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Monday
                {'day': 1, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Tuesday
                {'day': 3, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Thursday
                {'day': 4, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Friday
                {'day': 5, 'start': time(10, 0), 'end': time(14, 0), 'type': 'regular'},  # Saturday
            ],
            
            # Neurology - Specialist with emergency on-call
            'neurology': [
                {'day': 0, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Monday
                {'day': 1, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Tuesday
                {'day': 2, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Wednesday
                {'day': 3, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Thursday
                {'day': 4, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Friday
                {'day': 5, 'start': time(8, 0), 'end': time(12, 0), 'type': 'emergency'}, # Saturday emergency
                {'day': 6, 'start': time(8, 0), 'end': time(12, 0), 'type': 'emergency'}, # Sunday emergency
            ],
            
            # Orthopedics - Surgical specialist schedule
            'orthopedics': [
                {'day': 0, 'start': time(8, 0), 'end': time(16, 0), 'type': 'regular'},   # Monday
                {'day': 1, 'start': time(8, 0), 'end': time(16, 0), 'type': 'regular'},   # Tuesday
                {'day': 2, 'start': time(8, 0), 'end': time(16, 0), 'type': 'regular'},   # Wednesday
                {'day': 3, 'start': time(8, 0), 'end': time(16, 0), 'type': 'regular'},   # Thursday
                {'day': 4, 'start': time(8, 0), 'end': time(16, 0), 'type': 'regular'},   # Friday
                {'day': 5, 'start': time(10, 0), 'end': time(14, 0), 'type': 'emergency'}, # Saturday emergency
            ],
            
            # Ophthalmology - Eye specialist hours
            'ophthalmology': [
                {'day': 0, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Monday
                {'day': 1, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Tuesday
                {'day': 2, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Wednesday
                {'day': 4, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Friday
                {'day': 5, 'start': time(9, 0), 'end': time(13, 0), 'type': 'regular'},   # Saturday
            ],
            
            # ENT - Regular specialist schedule
            'ent': [
                {'day': 0, 'start': time(9, 30), 'end': time(17, 30), 'type': 'regular'},  # Monday
                {'day': 1, 'start': time(9, 30), 'end': time(17, 30), 'type': 'regular'},  # Tuesday
                {'day': 2, 'start': time(9, 30), 'end': time(17, 30), 'type': 'regular'},  # Wednesday
                {'day': 3, 'start': time(9, 30), 'end': time(17, 30), 'type': 'regular'},  # Thursday
                {'day': 4, 'start': time(9, 30), 'end': time(17, 30), 'type': 'regular'},  # Friday
                {'day': 5, 'start': time(10, 0), 'end': time(14, 0), 'type': 'regular'},   # Saturday
            ],
            
            # Gynecology - Women's health specialist
            'gynecology': [
                {'day': 0, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Monday
                {'day': 1, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Tuesday
                {'day': 2, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Wednesday
                {'day': 3, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Thursday
                {'day': 4, 'start': time(10, 0), 'end': time(18, 0), 'type': 'regular'},  # Friday
                {'day': 5, 'start': time(9, 0), 'end': time(13, 0), 'type': 'regular'},   # Saturday
                {'day': 6, 'start': time(9, 0), 'end': time(12, 0), 'type': 'emergency'}, # Sunday emergency
            ],
            
            # Pediatrics - Children's doctor with flexible hours
            'pediatrics': [
                {'day': 0, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Monday
                {'day': 1, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Tuesday
                {'day': 2, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Wednesday
                {'day': 3, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Thursday
                {'day': 4, 'start': time(9, 0), 'end': time(17, 0), 'type': 'regular'},   # Friday
                {'day': 5, 'start': time(9, 0), 'end': time(15, 0), 'type': 'regular'},   # Saturday
                {'day': 6, 'start': time(10, 0), 'end': time(14, 0), 'type': 'emergency'}, # Sunday emergency
            ],
            
            # Psychiatry - Mental health specialist
            'psychiatry': [
                {'day': 0, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Monday
                {'day': 1, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Tuesday
                {'day': 2, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Wednesday
                {'day': 3, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Thursday
                {'day': 4, 'start': time(11, 0), 'end': time(19, 0), 'type': 'regular'},  # Friday
                {'day': 5, 'start': time(10, 0), 'end': time(14, 0), 'type': 'regular'},  # Saturday
            ],
            
            # Emergency Medicine - 24/7 coverage in shifts
            'emergency': [
                {'day': 0, 'start': time(0, 0), 'end': time(23, 59), 'type': 'emergency'}, # Monday
                {'day': 1, 'start': time(0, 0), 'end': time(23, 59), 'type': 'emergency'}, # Tuesday
                {'day': 2, 'start': time(0, 0), 'end': time(23, 59), 'type': 'emergency'}, # Wednesday
                {'day': 3, 'start': time(0, 0), 'end': time(23, 59), 'type': 'emergency'}, # Thursday
                {'day': 4, 'start': time(0, 0), 'end': time(23, 59), 'type': 'emergency'}, # Friday
                {'day': 5, 'start': time(0, 0), 'end': time(23, 59), 'type': 'emergency'}, # Saturday
                {'day': 6, 'start': time(0, 0), 'end': time(23, 59), 'type': 'emergency'}, # Sunday
            ],
        }

    def create_availability_for_doctor(self, doctor, availability_templates):
        """Create availability schedule for a specific doctor."""
        
        # Skip if doctor already has availability (unless clearing)
        if DoctorAvailability.objects.filter(doctor=doctor).exists():
            return 0
        
        # Get template for doctor's specialty
        specialty = doctor.specialty
        template = availability_templates.get(specialty)
        
        # Use general template as fallback
        if not template:
            template = availability_templates['general']
            
        created_count = 0
        
        for slot in template:
            try:
                # Check if this exact slot already exists
                existing = DoctorAvailability.objects.filter(
                    doctor=doctor,
                    day_of_week=slot['day'],
                    start_time=slot['start'],
                    end_time=slot['end']
                ).exists()
                
                if not existing:
                    DoctorAvailability.objects.create(
                        doctor=doctor,
                        day_of_week=slot['day'],
                        start_time=slot['start'],
                        end_time=slot['end'],
                        is_active=True
                    )
                    created_count += 1
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Could not create slot for {doctor.first_name}: {str(e)}')
                )
        
        return created_count

    def get_random_variations(self):
        """Add some random variations to make schedules more realistic."""
        variations = [
            {'start_offset': 0, 'end_offset': 0},      # No change
            {'start_offset': 30, 'end_offset': 30},    # Start/end 30 min later
            {'start_offset': -30, 'end_offset': -30},  # Start/end 30 min earlier
            {'start_offset': 0, 'end_offset': 60},     # End 1 hour later
            {'start_offset': -30, 'end_offset': 0},    # Start 30 min earlier
        ]
        return random.choice(variations)