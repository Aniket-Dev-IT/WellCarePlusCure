"""
Management command to mask all phone numbers in the database for privacy protection.

This command updates all doctor and patient phone numbers to use masked format
(+91 XXXX-XXX-XXX) to prevent accidental calls to real numbers.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.doctors.models import Doctor
from apps.core.utils import get_demo_phone_number


class Command(BaseCommand):
    help = 'Mask all phone numbers in the database to prevent accidental calls'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm that you want to mask all phone numbers',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    'This command will mask ALL phone numbers in the database.\n'
                    'Use --confirm to proceed.'
                )
            )
            return

        # Update doctor phone numbers with unique masked numbers
        doctors_updated = 0
        for i, doctor in enumerate(Doctor.objects.all(), 1):
            if doctor.phone and not doctor.phone.startswith('+91 XXXX-XXX-'):
                # Create unique masked phone number to avoid unique constraint issues
                masked_phone = f'+91 XXXX-XXX-{i:03d}'
                doctor.phone = masked_phone
                doctor.save(update_fields=['phone'])
                doctors_updated += 1

        # Update user phone numbers (if User model has phone field)
        users_updated = 0
        for user in User.objects.all():
            if hasattr(user, 'phone') and user.phone and user.phone != masked_phone:
                user.phone = masked_phone
                user.save(update_fields=['phone'])
                users_updated += 1

        # Update patient profile phone numbers if they exist
        try:
            from apps.patients.models import PatientProfile
            patients_updated = 0
            for patient in PatientProfile.objects.all():
                if hasattr(patient, 'phone') and patient.phone and patient.phone != masked_phone:
                    patient.phone = masked_phone
                    patient.save(update_fields=['phone'])
                    patients_updated += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'Updated {patients_updated} patient phone numbers')
            )
        except ImportError:
            # PatientProfile model doesn't exist
            pass

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully masked phone numbers:\n'
                f'- Doctors: {doctors_updated}\n'
                f'- Users: {users_updated}\n'
                f'All phone numbers are now in format: +91 XXXX-XXX-XXX'
            )
        )
