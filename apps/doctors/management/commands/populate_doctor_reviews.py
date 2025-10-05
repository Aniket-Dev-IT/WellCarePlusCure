"""
Django management command to populate realistic patient reviews for doctors.

This command creates authentic Indian patient reviews for all doctors
with varied ratings, comments, and realistic distribution.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.doctors.models import Doctor, Review
from datetime import date, datetime, timedelta
import random
from django.utils import timezone


class Command(BaseCommand):
    help = 'Populate realistic patient reviews for all doctors'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing reviews before creating new ones',
        )
        parser.add_argument(
            '--doctor-id',
            type=int,
            help='Populate reviews for a specific doctor ID only',
        )
        parser.add_argument(
            '--reviews-per-doctor',
            type=int,
            default=6,
            help='Average number of reviews per doctor (default: 6)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('⭐ Populating doctor reviews...\n'))
        
        # Clear existing data if requested
        if options['clear_existing']:
            self.stdout.write('🗑️  Clearing existing reviews...')
            Review.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✅ Cleared existing reviews\n'))
        
        # Get doctors to process
        if options['doctor_id']:
            doctors = Doctor.objects.filter(id=options['doctor_id'])
            if not doctors.exists():
                self.stdout.write(self.style.ERROR(f'❌ Doctor with ID {options["doctor_id"]} not found'))
                return
        else:
            doctors = Doctor.objects.all()
        
        self.stdout.write(f'👩‍⚕️ Processing {doctors.count()} doctors...\n')
        
        # Get or create patient users for reviews
        patients = self.get_or_create_patients()
        
        # Review templates and data
        review_data = self.get_review_templates()
        
        # Track statistics
        total_created = 0
        doctors_updated = 0
        
        for doctor in doctors:
            try:
                reviews_per_doctor = options['reviews_per_doctor']
                # Add some randomness (3-10 reviews per doctor)
                num_reviews = random.randint(3, min(10, reviews_per_doctor + 4))
                
                created_count = self.create_reviews_for_doctor(doctor, patients, review_data, num_reviews)
                if created_count > 0:
                    doctors_updated += 1
                    total_created += created_count
                    self.stdout.write(
                        f'✅ Dr. {doctor.first_name} {doctor.last_name}: {created_count} reviews created'
                    )
                else:
                    self.stdout.write(
                        f'ℹ️  Dr. {doctor.first_name} {doctor.last_name}: Already has reviews'
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Error processing Dr. {doctor.first_name} {doctor.last_name}: {str(e)}')
                )
        
        # Update doctor statistics after creating reviews
        self.stdout.write('\n📊 Updating doctor statistics...')
        for doctor in doctors:
            try:
                doctor.update_statistics()
            except Exception as e:
                self.stdout.write(f'⚠️  Could not update stats for Dr. {doctor.first_name}: {str(e)}')
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(f'\n🎉 Summary:')
        )
        self.stdout.write(f'   👥 Doctors processed: {doctors_updated}/{doctors.count()}')
        self.stdout.write(f'   ⭐ Total reviews created: {total_created}')
        self.stdout.write(f'   🔄 You can now refresh the doctor profile pages to see the reviews!')

    def get_or_create_patients(self):
        """Get or create patient users for reviews."""
        
        # Indian patient names
        indian_names = [
            {'first': 'Aarav', 'last': 'Sharma'},
            {'first': 'Vivaan', 'last': 'Patel'},
            {'first': 'Aditya', 'last': 'Singh'},
            {'first': 'Vihaan', 'last': 'Kumar'},
            {'first': 'Arjun', 'last': 'Gupta'},
            {'first': 'Sai', 'last': 'Reddy'},
            {'first': 'Reyansh', 'last': 'Agarwal'},
            {'first': 'Ayaan', 'last': 'Verma'},
            {'first': 'Krishna', 'last': 'Joshi'},
            {'first': 'Ishaan', 'last': 'Mehta'},
            {'first': 'Aadhya', 'last': 'Nair'},
            {'first': 'Ananya', 'last': 'Iyer'},
            {'first': 'Saanvi', 'last': 'Rao'},
            {'first': 'Diya', 'last': 'Desai'},
            {'first': 'Pihu', 'last': 'Shah'},
            {'first': 'Myra', 'last': 'Malhotra'},
            {'first': 'Aanya', 'last': 'Sinha'},
            {'first': 'Ira', 'last': 'Bansal'},
            {'first': 'Kavya', 'last': 'Kapoor'},
            {'first': 'Kiara', 'last': 'Chopra'},
            {'first': 'Arya', 'last': 'Aggarwal'},
            {'first': 'Riya', 'last': 'Saxena'},
            {'first': 'Tanya', 'last': 'Jain'},
            {'first': 'Priya', 'last': 'Mishra'},
            {'first': 'Neha', 'last': 'Pandey'},
            {'first': 'Sneha', 'last': 'Tiwari'},
            {'first': 'Pooja', 'last': 'Dubey'},
            {'first': 'Divya', 'last': 'Shukla'},
            {'first': 'Meera', 'last': 'Bhargava'},
            {'first': 'Sonia', 'last': 'Srivastava'},
        ]
        
        patients = []
        
        for i, name_data in enumerate(indian_names):
            username = f"patient_{name_data['first'].lower()}_{name_data['last'].lower()}_{i}"
            email = f"{name_data['first'].lower()}.{name_data['last'].lower()}{i}@example.com"
            
            # Try to get existing user first
            try:
                user = User.objects.get(username=username)
                patients.append(user)
            except User.DoesNotExist:
                # Create new user if doesn't exist
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=name_data['first'],
                    last_name=name_data['last'],
                    password='patient123'  # Default password for demo patients
                )
                patients.append(user)
        
        return patients

    def get_review_templates(self):
        """Get review templates with varied content."""
        
        return {
            # 5-star reviews (Excellent)
            5: [
                {
                    'title': 'Excellent Doctor!',
                    'comments': [
                        'Dr. {doctor_name} is absolutely wonderful! Very professional and caring. The consultation was thorough and I felt completely comfortable. Highly recommended!',
                        'Outstanding doctor with great expertise. Explained everything clearly and patiently answered all my questions. The treatment was very effective.',
                        'Very impressed with the professional service. Dr. {doctor_name} is knowledgeable and compassionate. The clinic is also well-maintained.',
                        'Exceptional medical care! The doctor listened carefully to my concerns and provided the right treatment. I am very satisfied with the results.',
                        'Brilliant doctor! Very experienced and skilled. The consultation was detailed and the treatment plan was perfect. Would definitely recommend to others.',
                    ]
                },
                {
                    'title': 'Highly Recommended',
                    'comments': [
                        'Dr. {doctor_name} is one of the best doctors I have consulted. Very professional approach and excellent treatment. Thank you doctor!',
                        'Amazing experience! The doctor was very patient and explained the condition in detail. The prescribed medicines worked perfectly.',
                        'Fantastic doctor with great bedside manner. Made me feel at ease during the consultation. Very satisfied with the treatment outcome.',
                        'Excellent care and attention to detail. Dr. {doctor_name} is truly dedicated to patient welfare. The diagnosis was accurate and treatment effective.',
                        'Outstanding medical expertise combined with genuine care for patients. I am very grateful for the excellent treatment received.',
                    ]
                }
            ],
            
            # 4-star reviews (Very Good)
            4: [
                {
                    'title': 'Very Good Doctor',
                    'comments': [
                        'Dr. {doctor_name} is very good and experienced. The treatment was effective. Only issue was the waiting time was a bit long.',
                        'Good consultation and proper diagnosis. The doctor is knowledgeable but the clinic could be better organized.',
                        'Very professional doctor with good expertise. The treatment worked well. Would visit again if needed.',
                        'Positive experience overall. Dr. {doctor_name} explained the condition well and prescribed the right medicines.',
                        'Good doctor with proper knowledge. The consultation was helpful though it felt a bit rushed.',
                    ]
                },
                {
                    'title': 'Satisfied with Treatment',
                    'comments': [
                        'The doctor provided good care and the treatment was successful. The consultation fee is reasonable.',
                        'Dr. {doctor_name} is experienced and gave proper advice. The medicines prescribed were effective.',
                        'Good medical service. The doctor was professional and the treatment plan was appropriate.',
                        'Satisfied with the consultation. The doctor answered most of my questions and provided good treatment.',
                        'Overall positive experience. Dr. {doctor_name} is competent and the treatment showed good results.',
                    ]
                }
            ],
            
            # 3-star reviews (Average)
            3: [
                {
                    'title': 'Average Experience',
                    'comments': [
                        'Dr. {doctor_name} is okay but the waiting time was too long. The treatment was decent but expected more attention.',
                        'The consultation was average. Doctor seemed knowledgeable but was in a hurry. The fees are also quite high.',
                        'Decent doctor but the experience could be better. The clinic needs better management.',
                        'The treatment was fine but the consultation felt rushed. Dr. {doctor_name} could spend more time with patients.',
                        'Average service. The doctor is competent but the overall experience was not exceptional.',
                    ]
                }
            ],
            
            # 2-star reviews (Below Average)
            2: [
                {
                    'title': 'Not Satisfied',
                    'comments': [
                        'The consultation was very brief and felt rushed. Dr. {doctor_name} did not listen to all my concerns properly.',
                        'Expected better care for the fees charged. The waiting time was excessive and the treatment was not very effective.',
                        'The doctor seemed knowledgeable but was not very patient with questions. The overall experience was disappointing.',
                        'Not satisfied with the consultation. The doctor was in too much hurry and did not explain the condition properly.',
                        'Below average experience. The treatment took longer than expected and the follow-up was not adequate.',
                    ]
                }
            ],
            
            # 1-star reviews (Poor)
            1: [
                {
                    'title': 'Poor Experience',
                    'comments': [
                        'Very disappointed with the consultation. Dr. {doctor_name} was not attentive and the treatment was ineffective.',
                        'Poor service quality. The doctor did not listen to my concerns and seemed disinterested.',
                        'Not recommended. The consultation was rushed and the prescribed treatment did not work.',
                        'Very unsatisfactory experience. The doctor was unprofessional and the treatment was inadequate.',
                        'Waste of time and money. The consultation was brief and unhelpful.',
                    ]
                }
            ]
        }

    def create_reviews_for_doctor(self, doctor, patients, review_data, num_reviews):
        """Create reviews for a specific doctor."""
        
        # Skip if doctor already has reviews (unless clearing)
        if Review.objects.filter(doctor=doctor).exists():
            return 0
        
        # Rating distribution (realistic distribution)
        # 50% excellent (5 star), 30% very good (4 star), 15% average (3 star), 4% below average (2 star), 1% poor (1 star)
        rating_distribution = [5] * 50 + [4] * 30 + [3] * 15 + [2] * 4 + [1] * 1
        
        created_count = 0
        
        for i in range(num_reviews):
            try:
                # Select random patient
                patient = random.choice(patients)
                
                # Select rating based on distribution
                rating = random.choice(rating_distribution)
                
                # Get review template for this rating
                templates = review_data.get(rating, review_data[3])  # Fallback to average
                template = random.choice(templates)
                
                # Select random title and comment
                title = template['title']
                comment = random.choice(template['comments']).format(
                    doctor_name=f"Dr. {doctor.first_name} {doctor.last_name}"
                )
                
                # Generate random date within last 6 months
                end_date = timezone.now()
                start_date = end_date - timedelta(days=180)
                random_date = start_date + timedelta(
                    days=random.randint(0, (end_date - start_date).days)
                )
                
                # Check if this patient already reviewed this doctor
                existing = Review.objects.filter(doctor=doctor, patient=patient).exists()
                if existing:
                    continue
                
                # Create the review
                review = Review.objects.create(
                    doctor=doctor,
                    patient=patient,
                    rating=rating,
                    title=title,
                    comment=comment,
                    is_approved=True,
                    created_at=random_date
                )
                
                # Also set updated_at to the same time
                review.updated_at = random_date
                review.save(update_fields=['updated_at'])
                
                created_count += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Could not create review for Dr. {doctor.first_name}: {str(e)}')
                )
        
        return created_count

    def get_random_date_within_months(self, months=6):
        """Generate a random date within the specified number of months."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=months * 30)
        
        random_days = random.randint(0, (end_date - start_date).days)
        return start_date + timedelta(days=random_days)