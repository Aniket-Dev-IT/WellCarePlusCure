from django.core.management.base import BaseCommand
from apps.users.models import UserProfile
import os
from django.conf import settings


class Command(BaseCommand):
    help = 'Test patient photo matching to verify photos are being found correctly'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Testing patient photo matching...\n")
        
        # Get the list of available photos
        static_users_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'users')
        available_photos = []
        if os.path.exists(static_users_dir):
            available_photos = [f for f in os.listdir(static_users_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        
        self.stdout.write(f"📸 Available photos in {static_users_dir}:")
        for photo in sorted(available_photos):
            self.stdout.write(f"   - {photo}")
        self.stdout.write("")
        
        # Test each patient profile
        profiles = UserProfile.objects.all().order_by('full_name')
        
        self.stdout.write("👥 Testing patient photo matching:")
        matched_count = 0
        total_count = 0
        
        for profile in profiles:
            total_count += 1
            photo_url = profile.profile_picture_url
            
            # Check if it's using a real photo (not default)
            is_matched = 'default-user.png' not in photo_url
            
            if is_matched:
                matched_count += 1
                status = "✅ MATCHED"
            else:
                status = "❌ NO MATCH"
            
            self.stdout.write(f"   {status}: {profile.full_name} ({profile.user.username}) -> {photo_url}")
        
        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"   Total profiles: {total_count}")
        self.stdout.write(f"   Matched photos: {matched_count}")
        self.stdout.write(f"   Using default: {total_count - matched_count}")
        if total_count > 0:
            self.stdout.write(f"   Match rate: {(matched_count/total_count*100):.1f}%")
