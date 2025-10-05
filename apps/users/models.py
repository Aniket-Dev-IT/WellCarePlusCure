from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.urls import reverse
from PIL import Image


class UserProfile(models.Model):
    """
    Extended user profile model for patients.
    
    This model stores additional information about users/patients
    including contact details, preferences, and medical history.
    """
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
        ('P', 'Prefer not to say'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    
    # Core relationship
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    
    # Personal Information
    full_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Full name of the user"
    )
    date_of_birth = models.DateField(
        null=True,
        blank=True,
        help_text="Date of birth"
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        help_text="Gender"
    )
    
    # Contact Information
    phone_regex = RegexValidator(
        regex=r'^[\+\(]?[0-9][\d\s\-\(\)]*$',
        message="Phone number can contain digits, spaces, dashes, parentheses, and + sign. Examples: +91 9876543210, (555) 123-4567, 555-123-4567"
    )
    phone = models.CharField(
        validators=[phone_regex],
        max_length=20,
        blank=True,
        help_text="Primary contact phone number (e.g., +91 9876543210, (555) 123-4567)"
    )
    alternate_phone = models.CharField(
        validators=[phone_regex],
        max_length=20,
        blank=True,
        help_text="Alternate contact phone number (e.g., +91 9876543210, (555) 123-4567)"
    )
    
    # Address Information
    address_line1 = models.CharField(
        max_length=255,
        blank=True,
        help_text="Address line 1"
    )
    address_line2 = models.CharField(
        max_length=255,
        blank=True,
        help_text="Address line 2 (optional)"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        help_text="City"
    )
    state = models.CharField(
        max_length=100,
        blank=True,
        help_text="State/Province"
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text="Postal/ZIP code"
    )
    country = models.CharField(
        max_length=100,
        default='India',
        help_text="Country"
    )
    
    # Medical Information
    blood_group = models.CharField(
        max_length=3,
        choices=BLOOD_GROUP_CHOICES,
        blank=True,
        help_text="Blood group"
    )
    allergies = models.TextField(
        blank=True,
        help_text="Known allergies (separate with commas)"
    )
    chronic_conditions = models.TextField(
        blank=True,
        help_text="Chronic medical conditions"
    )
    medications = models.TextField(
        blank=True,
        help_text="Current medications"
    )
    
    # Emergency Contact
    emergency_contact_name = models.CharField(
        max_length=200,
        blank=True,
        help_text="Emergency contact person name"
    )
    emergency_contact_phone = models.CharField(
        validators=[phone_regex],
        max_length=20,
        blank=True,
        help_text="Emergency contact phone number (e.g., +91 9876543210, (555) 123-4567)"
    )
    emergency_contact_relation = models.CharField(
        max_length=100,
        blank=True,
        help_text="Relationship with emergency contact"
    )
    
    # Profile Picture
    profile_picture = models.ImageField(
        upload_to='users/profiles/%Y/%m/',
        default='users/profiles/default.png',
        help_text="Profile picture"
    )
    
    # Preferences
    email_notifications = models.BooleanField(
        default=True,
        help_text="Receive email notifications"
    )
    sms_notifications = models.BooleanField(
        default=True,
        help_text="Receive SMS notifications"
    )
    
    # Additional profile information
    occupation = models.CharField(
        max_length=200,
        blank=True,
        help_text="Current occupation"
    )
    insurance_provider = models.CharField(
        max_length=200,
        blank=True,
        help_text="Health insurance provider"
    )
    insurance_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Health insurance policy number"
    )
    
    # Activity tracking
    last_appointment_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Date of last appointment"
    )
    total_appointments = models.PositiveIntegerField(
        default=0,
        help_text="Total number of appointments booked"
    )
    
    # Verification status
    is_phone_verified = models.BooleanField(
        default=False,
        help_text="Whether phone number is verified"
    )
    is_email_verified = models.BooleanField(
        default=False,
        help_text="Whether email is verified"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}'s Profile"
    
    @property
    def full_address(self):
        """Return formatted full address."""
        address_parts = []
        if self.address_line1:
            address_parts.append(self.address_line1)
        if self.address_line2:
            address_parts.append(self.address_line2)
        if self.city:
            address_parts.append(self.city)
        if self.state:
            address_parts.append(self.state)
        if self.postal_code:
            address_parts.append(self.postal_code)
        # Only include country if it's not the default 'India' OR if we have a complete address
        if self.country and self.country != 'India':
            address_parts.append(self.country)
        elif self.country == 'India' and self.address_line1 and self.postal_code:
            # Include India only if we have a street address and postal code
            address_parts.append(self.country)
        return ', '.join(address_parts)
    
    @property
    def age(self):
        """Calculate age from date of birth."""
        if not self.date_of_birth:
            return None
        
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def profile_picture_url(self):
        """Return the profile picture URL using static images."""
        from django.templatetags.static import static
        import os
        from django.conf import settings
        
        # Build list of possible names to match against photos
        possible_names = []
        
        # Add full name parts
        if self.full_name:
            name_parts = self.full_name.strip().split()
            if name_parts:
                # Try first name from full_name
                possible_names.append(name_parts[0])
        
        # Add user first name
        if self.user.first_name:
            possible_names.append(self.user.first_name)
        
        # Add name from username (cleaned up)
        if self.user.username:
            username_clean = self.user.username.replace('.patient', '').replace('.doctor', '').replace('dr.', '')
            # Handle usernames like "aarnav.patient" -> "Aarnav"
            if '.' in username_clean:
                username_clean = username_clean.split('.')[0]
            possible_names.append(username_clean.title())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_names = []
        for name in possible_names:
            if name and name not in seen:
                seen.add(name)
                unique_names.append(name)
        
        # Try to find matching static image
        static_users_dir = os.path.join(settings.BASE_DIR, 'static', 'images', 'users')
        
        for name in unique_names:
            for extension in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                filename = f"{name}{extension}"
                full_static_path = os.path.join(static_users_dir, filename)
                if os.path.exists(full_static_path):
                    static_path = f"images/users/{filename}"
                    return static(static_path)
        
        # Fallback: check if any photo exists with case-insensitive matching
        if os.path.exists(static_users_dir):
            try:
                available_files = os.listdir(static_users_dir)
                for name in unique_names:
                    for available_file in available_files:
                        # Case-insensitive match on the base name
                        file_base = os.path.splitext(available_file)[0].lower()
                        if name.lower() == file_base:
                            static_path = f"images/users/{available_file}"
                            return static(static_path)
            except OSError:
                pass
        
        # Return default photo if no matching static image found
        return static('images/default-user.png')
    
    def get_absolute_url(self):
        """Return the absolute URL for this profile."""
        return reverse('users:profile', kwargs={'pk': self.pk})
    
    def update_appointment_stats(self):
        """Update user's appointment statistics."""
        from apps.doctors.models import Appointment
        
        # Get latest appointment
        latest_appointment = Appointment.objects.filter(
            patient=self.user
        ).order_by('-appointment_date', '-appointment_time').first()
        
        if latest_appointment:
            self.last_appointment_date = latest_appointment.appointment_datetime
        
        # Update total appointments count
        self.total_appointments = Appointment.objects.filter(
            patient=self.user
        ).count()
        
        self.save(update_fields=['last_appointment_date', 'total_appointments'])
    
    def save(self, *args, **kwargs):
        """Override save to handle profile picture resizing."""
        super().save(*args, **kwargs)
        
        if self.profile_picture and hasattr(self.profile_picture, 'path'):
            try:
                import os
                if os.path.exists(self.profile_picture.path):
                    img = Image.open(self.profile_picture.path)
                    if img.height > 300 or img.width > 300:
                        output_size = (300, 300)
                        img.thumbnail(output_size)
                        img.save(self.profile_picture.path)
            except (IOError, OSError):
                # Handle missing file gracefully (e.g., during testing)
                pass
