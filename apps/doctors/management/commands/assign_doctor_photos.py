import os
import glob
from django.core.management.base import BaseCommand
from django.core.files import File
from django.conf import settings
from apps.doctors.models import Doctor
from fuzzywuzzy import fuzz
import shutil


class Command(BaseCommand):
    help = 'Assign existing doctor photos to Doctor records based on name matching'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--threshold',
            type=int,
            default=70,
            help='Fuzzy matching threshold (default: 70)',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        threshold = options['threshold']
        
        self.stdout.write("Starting doctor photo assignment...")
        
        # Get all doctors without photos
        doctors = Doctor.objects.all()
        doctors_without_photos = doctors.filter(photo__isnull=True).count()
        doctors_with_photos = doctors.filter(photo__isnull=False).count()
        
        self.stdout.write(f"Total doctors: {doctors.count()}")
        self.stdout.write(f"Doctors without photos: {doctors_without_photos}")
        self.stdout.write(f"Doctors with photos: {doctors_with_photos}")
        
        # Search for photo files in multiple directories
        photo_dirs = [
            os.path.join(settings.MEDIA_ROOT, 'doctors_pics'),
            os.path.join(settings.MEDIA_ROOT, 'doctors', 'photos', '2025', '09'),
            os.path.join(settings.MEDIA_ROOT, 'tewm'),
        ]
        
        photo_files = []
        for photo_dir in photo_dirs:
            if os.path.exists(photo_dir):
                # Find all image files
                patterns = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
                for pattern in patterns:
                    photo_files.extend(glob.glob(os.path.join(photo_dir, pattern)))
        
        self.stdout.write(f"Found {len(photo_files)} photo files")
        
        # Create a mapping of photo files to doctor names (extracted from filename)
        photo_mapping = {}
        for photo_path in photo_files:
            filename = os.path.basename(photo_path)
            # Remove common prefixes and extensions
            name = filename.replace('Dr ', '').replace('Dr. ', '').replace('.jpg', '').replace('.jpeg', '').replace('.png', '')
            photo_mapping[name] = photo_path
            
        self.stdout.write(f"Created mapping for {len(photo_mapping)} photo names")
        
        # Try to match doctors with photos
        matches_found = 0
        assignments_made = 0
        
        for doctor in doctors:
            if doctor.photo:
                continue  # Skip doctors who already have photos
                
            best_match = None
            best_score = 0
            best_path = None
            
            # Create doctor search names
            doctor_names = [
                doctor.display_name,
                f"{doctor.first_name} {doctor.last_name}",
                doctor.first_name,
                doctor.last_name,
                doctor.user.username,
            ]
            
            # Try to find the best matching photo
            for doctor_name in doctor_names:
                if not doctor_name:
                    continue
                    
                for photo_name, photo_path in photo_mapping.items():
                    # Use fuzzy matching to find similar names
                    score = fuzz.ratio(doctor_name.lower(), photo_name.lower())
                    
                    if score > best_score:
                        best_score = score
                        best_match = photo_name
                        best_path = photo_path
            
            if best_score >= threshold:
                matches_found += 1
                self.stdout.write(
                    f"Match found: {doctor.display_name} -> {best_match} (score: {best_score})"
                )
                
                if not dry_run:
                    try:
                        # Copy the file to the proper location
                        relative_path = f"doctors/photos/{os.path.basename(best_path)}"
                        destination = os.path.join(settings.MEDIA_ROOT, relative_path)
                        
                        # Create directory if it doesn't exist
                        os.makedirs(os.path.dirname(destination), exist_ok=True)
                        
                        # Copy file to destination
                        shutil.copy2(best_path, destination)
                        
                        # Update the doctor's photo field
                        doctor.photo = relative_path
                        doctor.save()
                        
                        assignments_made += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ Assigned photo to {doctor.display_name}")
                        )
                        
                        # Remove this photo from mapping to avoid duplicate assignments
                        del photo_mapping[best_match]
                        
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"✗ Error assigning photo to {doctor.display_name}: {e}")
                        )
        
        # Summary
        self.stdout.write(f"\n=== SUMMARY ===")
        self.stdout.write(f"Matches found: {matches_found}")
        
        if dry_run:
            self.stdout.write(f"Assignments would be made: {matches_found}")
            self.stdout.write("Run without --dry-run to apply changes")
        else:
            self.stdout.write(f"Assignments made: {assignments_made}")
            
            # Update doctors without photos to use default
            remaining_doctors = Doctor.objects.filter(photo__isnull=True)
            self.stdout.write(f"Doctors still without photos: {remaining_doctors.count()}")
            
        self.stdout.write("Doctor photo assignment completed!")
