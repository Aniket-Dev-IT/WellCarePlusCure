import json
import os
from datetime import datetime, date
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings
from apps.users.models import UserProfile
from apps.doctors.models import Doctor, DoctorEducation, DoctorSpecialization


class Command(BaseCommand):
    help = 'Load sample users and doctors data from JSON files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users-file',
            type=str,
            default='sample_data/users_data_with_credentials.json',
            help='Path to users JSON file'
        )
        parser.add_argument(
            '--doctors-file',
            type=str,
            default='sample_data/doctors_data_with_credentials.json',
            help='Path to doctors JSON file'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading'
        )

    def handle(self, *args, **options):
        users_file = options['users_file']
        doctors_file = options['doctors_file']
        clear_data = options['clear']

        # Check if files exist
        if not os.path.exists(users_file):
            raise CommandError(f'Users file does not exist: {users_file}')
        if not os.path.exists(doctors_file):
            raise CommandError(f'Doctors file does not exist: {doctors_file}')

        try:
            with transaction.atomic():
                if clear_data:
                    self.stdout.write('Clearing existing data...')
                    self.clear_existing_data()

                self.stdout.write('Loading users data...')
                users_created = self.load_users(users_file)
                
                self.stdout.write('Loading doctors data...')
                doctors_created = self.load_doctors(doctors_file)

                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully loaded {users_created} users and {doctors_created} doctors'
                    )
                )

        except Exception as e:
            raise CommandError(f'Error loading data: {str(e)}')

    def clear_existing_data(self):
        """Clear existing sample data"""
        # Clear doctors and related data
        DoctorSpecialization.objects.all().delete()
        DoctorEducation.objects.all().delete()
        Doctor.objects.all().delete()
        
        # Clear user profiles (but keep admin)
        UserProfile.objects.exclude(user__is_superuser=True).delete()
        User.objects.filter(is_superuser=False, is_staff=False).delete()

    def load_users(self, file_path):
        """Load users from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        users_created = 0
        for user_data in data['users']:
            try:
                # Check if user already exists
                if User.objects.filter(username=user_data['username']).exists():
                    self.stdout.write(f'User {user_data["username"]} already exists, skipping...')
                    continue

                # Create user
                user = User.objects.create_user(
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    is_staff=user_data.get('is_staff', False),
                    is_superuser=user_data.get('is_superuser', False)
                )

                # Create user profile if profile data exists
                if 'profile' in user_data:
                    profile_data = user_data['profile']
                    
                    # Convert date string to date object
                    date_of_birth = None
                    if profile_data.get('date_of_birth'):
                        date_of_birth = datetime.strptime(
                            profile_data['date_of_birth'], 
                            '%Y-%m-%d'
                        ).date()

                    # Create or get profile
                    profile, created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'date_of_birth': date_of_birth,
                            'gender': profile_data.get('gender', ''),
                            'phone': profile_data.get('phone', ''),
                            'alternate_phone': profile_data.get('alternate_phone', ''),
                            'address_line1': profile_data.get('address_line1', ''),
                            'address_line2': profile_data.get('address_line2', ''),
                            'city': profile_data.get('city', ''),
                            'state': profile_data.get('state', ''),
                            'postal_code': profile_data.get('postal_code', ''),
                            'country': profile_data.get('country', 'India'),
                            'blood_group': profile_data.get('blood_group', ''),
                            'allergies': profile_data.get('allergies', ''),
                            'chronic_conditions': profile_data.get('chronic_conditions', ''),
                            'medications': profile_data.get('medications', ''),
                            'emergency_contact_name': profile_data.get('emergency_contact_name', ''),
                            'emergency_contact_phone': profile_data.get('emergency_contact_phone', ''),
                            'emergency_contact_relation': profile_data.get('emergency_contact_relation', ''),
                            'occupation': profile_data.get('occupation', ''),
                            'insurance_provider': profile_data.get('insurance_provider', ''),
                            'insurance_number': profile_data.get('insurance_number', ''),
                            'email_notifications': profile_data.get('email_notifications', True),
                            'sms_notifications': profile_data.get('sms_notifications', True),
                        }
                    )

                    # Handle profile picture if specified
                    if profile_data.get('profile_picture'):
                        profile.profile_picture = profile_data['profile_picture']
                        profile.save()

                users_created += 1
                self.stdout.write(f'Created user: {user.username}')

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'Error creating user {user_data["username"]}: {str(e)}'
                    )
                )
                continue

        return users_created

    def load_doctors(self, file_path):
        """Load doctors from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        doctors_created = 0
        for doctor_data in data['doctors']:
            try:
                # Check if doctor user already exists
                if User.objects.filter(username=doctor_data['username']).exists():
                    self.stdout.write(f'Doctor {doctor_data["username"]} already exists, skipping...')
                    continue

                # Create user for doctor
                user = User.objects.create_user(
                    username=doctor_data['username'],
                    email=doctor_data['email'],
                    password=doctor_data['password'],
                    first_name=doctor_data['first_name'],
                    last_name=doctor_data['last_name'],
                    is_staff=doctor_data.get('is_staff', False),
                    is_superuser=doctor_data.get('is_superuser', False)
                )

                # Create doctor profile
                doctor_profile_data = doctor_data['doctor_profile']
                doctor = Doctor.objects.create(
                    user=user,
                    first_name=doctor_profile_data['first_name'],
                    last_name=doctor_profile_data['last_name'],
                    phone=doctor_profile_data['phone'],
                    email=doctor_profile_data['email'],
                    specialty=doctor_profile_data['specialty'],
                    qualification=doctor_profile_data['qualification'],
                    experience_years=doctor_profile_data['experience_years'],
                    consultation_fee=doctor_profile_data['consultation_fee'],
                    state=doctor_profile_data['state'],
                    city=doctor_profile_data['city'],
                    address=doctor_profile_data['address'],
                    photo=doctor_profile_data['photo'],
                    bio=doctor_profile_data['bio'],
                    is_available=doctor_profile_data.get('is_available', True),
                    is_verified=doctor_profile_data.get('is_verified', True),
                    medical_license_number=doctor_profile_data.get('medical_license_number', ''),
                    languages_spoken=doctor_profile_data.get('languages_spoken', 'English'),
                    hospital_affiliations=doctor_profile_data.get('hospital_affiliations', ''),
                    average_rating=doctor_profile_data.get('average_rating', 0.00),
                    total_reviews=doctor_profile_data.get('total_reviews', 0),
                    total_patients=doctor_profile_data.get('total_patients', 0),
                    website=doctor_profile_data.get('website', ''),
                    linkedin_profile=doctor_profile_data.get('linkedin_profile', ''),
                    clinic_name=doctor_profile_data.get('clinic_name', ''),
                    practice_start_year=doctor_profile_data.get('practice_start_year')
                )

                # Create education records
                if 'education' in doctor_data:
                    for edu_data in doctor_data['education']:
                        DoctorEducation.objects.create(
                            doctor=doctor,
                            degree_type=edu_data['degree_type'],
                            degree_name=edu_data['degree_name'],
                            institution=edu_data['institution'],
                            year_completed=edu_data['year_completed'],
                            grade_or_score=edu_data.get('grade_or_score', '')
                        )

                # Create specialization records
                if 'specializations' in doctor_data:
                    for spec_data in doctor_data['specializations']:
                        DoctorSpecialization.objects.create(
                            doctor=doctor,
                            name=spec_data['name'],
                            description=spec_data['description'],
                            years_of_experience=spec_data['years_of_experience'],
                            is_primary=spec_data.get('is_primary', False)
                        )

                doctors_created += 1
                self.stdout.write(f'Created doctor: Dr. {doctor.first_name} {doctor.last_name}')

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(
                        f'Error creating doctor {doctor_data["username"]}: {str(e)}'
                    )
                )
                continue

        return doctors_created
