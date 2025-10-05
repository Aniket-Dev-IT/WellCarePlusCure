"""
Django Management Command to Update Doctor Specialties
Maps old specialty values to new ones that match Quick Health Checkup categories
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.doctors.models import Doctor


class Command(BaseCommand):
    help = 'Update doctor specialties to match Quick Health Checkup categories'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Updating doctor specialties...'))
        
        # Mapping from old specialty values to new ones
        specialty_mapping = {
            'neurosurgery': 'neurology',
            'cardiac_surgery': 'cardiology',
            'dentistry': 'general',
            'gynecologic_oncology': 'gynecology',
            'plastic_surgery': 'general',
            'general_medicine': 'general',
            'acupuncture': 'general',
        }
        
        with transaction.atomic():
            doctors = Doctor.objects.all()
            updated_count = 0
            
            for doctor in doctors:
                old_specialty = doctor.specialty
                
                # Check if we need to map the specialty
                if old_specialty in specialty_mapping:
                    new_specialty = specialty_mapping[old_specialty]
                    doctor.specialty = new_specialty
                    doctor.save(update_fields=['specialty'])
                    
                    self.stdout.write(f'Updated Dr. {doctor.first_name} {doctor.last_name}: {old_specialty} → {new_specialty}')
                    updated_count += 1
                else:
                    # Check if specialty is still valid
                    valid_specialties = [choice[0] for choice in Doctor.SPECIALTIES]
                    if old_specialty not in valid_specialties:
                        # Default to general medicine
                        doctor.specialty = 'general'
                        doctor.save(update_fields=['specialty'])
                        
                        self.stdout.write(f'Updated Dr. {doctor.first_name} {doctor.last_name}: {old_specialty} → general (default)')
                        updated_count += 1
                    else:
                        self.stdout.write(f'Dr. {doctor.first_name} {doctor.last_name}: {old_specialty} (no change needed)')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully updated {updated_count} doctor specialties!'
                )
            )
