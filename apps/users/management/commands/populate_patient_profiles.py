from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.users.models import UserProfile
from datetime import date, datetime
import random
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Populate patient profiles with complete data and profile pictures'

    def handle(self, *args, **options):
        self.stdout.write("🚀 Populating patient profiles with complete data...\n")
        
        # Get all user profiles
        profiles = UserProfile.objects.all()
        
        # Sample data for realistic profiles
        cities = [
            'Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Kolkata', 'Hyderabad',
            'Pune', 'Jaipur', 'Lucknow', 'Ahmedabad', 'Gurgaon', 'Noida',
            'Chandigarh', 'Kochi', 'Surat', 'Indore', 'Bhopal', 'Coimbatore'
        ]
        
        states = [
            'Delhi', 'Maharashtra', 'Karnataka', 'Tamil Nadu', 'West Bengal', 'Telangana',
            'Maharashtra', 'Rajasthan', 'Uttar Pradesh', 'Gujarat', 'Haryana', 'Uttar Pradesh',
            'Punjab', 'Kerala', 'Gujarat', 'Madhya Pradesh', 'Madhya Pradesh', 'Tamil Nadu'
        ]
        
        occupations = [
            'Software Engineer', 'Business Analyst', 'Marketing Manager', 'Teacher', 'Doctor',
            'Lawyer', 'Accountant', 'Sales Executive', 'Designer', 'Consultant',
            'Student', 'Engineer', 'Manager', 'Developer', 'Analyst',
            'Professor', 'Architect', 'Pharmacist', 'Nurse', 'Administrator'
        ]
        
        blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
        
        allergies_list = [
            'Peanuts, Dust mites', 'Penicillin', 'Shellfish', 'Pollen, Cats',
            'Latex', 'Iodine', 'Aspirin', 'Dairy products',
            'Eggs, Nuts', 'None known', 'Seasonal allergens', 'Pet dander'
        ]
        
        conditions_list = [
            'Hypertension', 'Diabetes Type 2', 'Asthma', 'Arthritis',
            'Migraine', 'High cholesterol', 'None', 'GERD',
            'Thyroid disorder', 'None known', 'Back pain', 'Anxiety'
        ]
        
        insurance_providers = [
            'Star Health Insurance', 'HDFC ERGO', 'ICICI Lombard', 'Bajaj Allianz',
            'New India Assurance', 'Oriental Insurance', 'United India Insurance',
            'National Insurance', 'Max Bupa', 'Apollo Munich', 'Religare Health'
        ]
        
        updated_count = 0
        
        for i, profile in enumerate(profiles):
            updated = False
            
            # Update full_name if missing
            if not profile.full_name:
                if profile.user.first_name and profile.user.last_name:
                    profile.full_name = f"{profile.user.first_name} {profile.user.last_name}"
                elif profile.user.first_name:
                    profile.full_name = profile.user.first_name
                else:
                    # Generate name from username
                    username_parts = profile.user.username.replace('.patient', '').replace('.', ' ').split()
                    profile.full_name = ' '.join(word.title() for word in username_parts)
                updated = True
            
            # Update date of birth if missing
            if not profile.date_of_birth:
                year = random.randint(1970, 2005)
                month = random.randint(1, 12)
                day = random.randint(1, 28)
                profile.date_of_birth = date(year, month, day)
                updated = True
            
            # Update gender if missing
            if not profile.gender:
                profile.gender = random.choice(['M', 'F', 'O'])
                updated = True
            
            # Update phone if missing
            if not profile.phone:
                profile.phone = f"+91{random.randint(9000000000, 9999999999)}"
                updated = True
            
            # Update address if missing
            if not profile.city:
                profile.city = random.choice(cities)
                profile.state = states[cities.index(profile.city)]
                profile.country = 'India'
                profile.postal_code = f"{random.randint(100000, 999999)}"
                profile.address_line1 = f"{random.randint(1, 999)} {random.choice(['Main Road', 'Park Street', 'MG Road', 'Gandhi Nagar', 'Sector'])}"
                updated = True
            
            # Update blood group if missing
            if not profile.blood_group:
                profile.blood_group = random.choice(blood_groups)
                updated = True
            
            # Update allergies if missing
            if not profile.allergies:
                profile.allergies = random.choice(allergies_list)
                updated = True
            
            # Update chronic conditions if missing
            if not profile.chronic_conditions:
                profile.chronic_conditions = random.choice(conditions_list)
                updated = True
            
            # Update occupation if missing
            if not profile.occupation:
                profile.occupation = random.choice(occupations)
                updated = True
            
            # Update insurance if missing
            if not profile.insurance_provider:
                profile.insurance_provider = random.choice(insurance_providers)
                profile.insurance_number = f"POL{random.randint(1000000, 9999999)}"
                updated = True
            
            # Update emergency contact if missing
            if not profile.emergency_contact_name:
                relations = ['Father', 'Mother', 'Spouse', 'Sibling', 'Friend']
                relation = random.choice(relations)
                profile.emergency_contact_name = f"{profile.full_name.split()[0]} {relation}"
                profile.emergency_contact_phone = f"+91{random.randint(9000000000, 9999999999)}"
                profile.emergency_contact_relation = relation
                updated = True
            
            # Set verification status
            if not profile.is_phone_verified:
                profile.is_phone_verified = random.choice([True, False])
                profile.is_email_verified = random.choice([True, False])
                updated = True
            
            if updated:
                profile.save()
                updated_count += 1
                self.stdout.write(f"✓ Updated profile for {profile.full_name} ({profile.user.username})")
        
        # Now create/ensure default profile pictures exist
        self.create_default_images()
        
        self.stdout.write(f"\n🎉 Profile population completed!")
        self.stdout.write(f"Updated {updated_count} profiles")
        self.stdout.write("\n📸 Profile pictures will use default images or user-specific static images")

    def create_default_images(self):
        """Create placeholder profile images in static directory if they don't exist"""
        
        static_images_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'users')
        
        # Ensure the directory exists
        os.makedirs(static_images_dir, exist_ok=True)
        
        # Create a simple default image if it doesn't exist
        default_image_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'default-user.png')
        
        if not os.path.exists(default_image_path):
            self.stdout.write("📸 Creating default user avatar...")
            try:
                from PIL import Image, ImageDraw, ImageFont
                
                # Create a simple default avatar
                img = Image.new('RGB', (300, 300), color='#f0f0f0')
                draw = ImageDraw.Draw(img)
                
                # Draw a circle for avatar
                draw.ellipse([50, 50, 250, 250], fill='#4CAF50', outline='#45a049', width=3)
                
                # Add user icon (simple)
                draw.ellipse([115, 90, 185, 160], fill='white')  # Head
                draw.ellipse([95, 160, 205, 220], fill='white')   # Body
                
                # Ensure directory exists
                os.makedirs(os.path.dirname(default_image_path), exist_ok=True)
                img.save(default_image_path)
                
                self.stdout.write("✓ Created default-user.png")
                
            except ImportError:
                self.stdout.write("⚠ PIL not available, skipping image creation")
            except Exception as e:
                self.stdout.write(f"⚠ Error creating default image: {e}")
        
        # Create sample user avatars for some common names
        sample_names = [
            'aarnav', 'aarohi', 'advik', 'isha', 'ivaan', 'kalp', 'zayn',
            'abhishek', 'akash', 'ananya', 'arjun', 'divya', 'kavya',
            'manish', 'neha', 'priya', 'rahul', 'sakshi', 'shreya'
        ]
        
        for name in sample_names:
            avatar_path = os.path.join(static_images_dir, f"{name.title()}.jpg")
            if not os.path.exists(avatar_path):
                try:
                    from PIL import Image, ImageDraw
                    
                    # Create personalized avatar with different colors
                    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8']
                    color = colors[hash(name) % len(colors)]
                    
                    img = Image.new('RGB', (300, 300), color='#f8f9fa')
                    draw = ImageDraw.Draw(img)
                    
                    # Draw a circle avatar with name initial
                    draw.ellipse([30, 30, 270, 270], fill=color, outline='#333', width=2)
                    
                    # Add initial letter
                    font_size = 120
                    try:
                        # Try to use a font, fallback to default
                        font = ImageFont.load_default()
                    except:
                        font = None
                    
                    initial = name[0].upper()
                    text_bbox = draw.textbbox((0, 0), initial, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    x = (300 - text_width) // 2
                    y = (300 - text_height) // 2 - 10
                    
                    draw.text((x, y), initial, fill='white', font=font)
                    
                    img.save(avatar_path)
                    
                except Exception as e:
                    # Skip if there's an error creating the image
                    continue
        
        self.stdout.write(f"✓ Sample avatar images checked/created in {static_images_dir}")
