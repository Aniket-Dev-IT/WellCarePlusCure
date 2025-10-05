import random
from datetime import datetime, timedelta, date, time
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from apps.doctors.models import Doctor, Appointment
from apps.users.models import UserProfile


class Command(BaseCommand):
    help = 'Create sample appointments for testing dashboard functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=50,
            help='Number of sample appointments to create'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing appointments before creating new ones'
        )

    def handle(self, *args, **options):
        count = options['count']
        clear_existing = options['clear']

        if clear_existing:
            self.stdout.write('Clearing existing appointments...')
            Appointment.objects.all().delete()

        # Get available patients and doctors
        patients = User.objects.filter(is_staff=False, is_superuser=False).exclude(doctor_profile__isnull=False)
        doctors = Doctor.objects.all()

        if not patients.exists():
            self.stdout.write(self.style.ERROR('No patients found. Please create some users first.'))
            return

        if not doctors.exists():
            self.stdout.write(self.style.ERROR('No doctors found. Please create some doctors first.'))
            return

        self.stdout.write(f'Creating {count} sample appointments...')

        appointments_created = 0
        max_attempts = count * 3  # Avoid infinite loops

        # Define realistic appointment scenarios
        statuses = [
            ('scheduled', 0.3),  # 30% scheduled
            ('confirmed', 0.25), # 25% confirmed
            ('completed', 0.35), # 35% completed
            ('cancelled', 0.05), # 5% cancelled
            ('no_show', 0.03),   # 3% no show
            ('in_progress', 0.02) # 2% in progress
        ]

        # Create appointments spanning last 3 months to next 2 months
        start_date = timezone.now().date() - timedelta(days=90)
        end_date = timezone.now().date() + timedelta(days=60)

        for attempt in range(max_attempts):
            if appointments_created >= count:
                break

            try:
                # Select random patient and doctor
                patient = random.choice(patients)
                doctor = random.choice(doctors)

                # Generate random appointment date
                random_date = start_date + timedelta(
                    days=random.randint(0, (end_date - start_date).days)
                )

                # Generate realistic appointment time (9 AM to 6 PM)
                hour = random.choice([9, 10, 11, 14, 15, 16, 17, 18])
                minute = random.choice([0, 15, 30, 45])
                appointment_time = time(hour=hour, minute=minute)

                # Check if this slot is already taken
                if Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date=random_date,
                    appointment_time=appointment_time
                ).exists():
                    continue

                # Select status based on date
                if random_date > timezone.now().date():
                    # Future appointments
                    status = random.choices(
                        ['scheduled', 'confirmed'],
                        weights=[0.4, 0.6]
                    )[0]
                elif random_date == timezone.now().date():
                    # Today's appointments
                    status = random.choices(
                        ['scheduled', 'confirmed', 'in_progress'],
                        weights=[0.3, 0.5, 0.2]
                    )[0]
                else:
                    # Past appointments
                    status = random.choices(
                        ['completed', 'cancelled', 'no_show'],
                        weights=[0.85, 0.10, 0.05]
                    )[0]

                # Generate patient notes
                symptoms_list = [
                    "Feeling unwell with fever and headache",
                    "Chest pain and difficulty breathing",
                    "Skin rash and itching",
                    "Back pain and stiffness",
                    "Stomach ache and nausea",
                    "Routine checkup",
                    "Follow-up appointment",
                    "Vaccination appointment",
                    "Regular consultation",
                    "Health screening",
                    "Joint pain in knees",
                    "Eye irritation and redness",
                    "Persistent cough",
                    "Sleep issues",
                    "Stress and anxiety",
                ]

                patient_notes = random.choice(symptoms_list)

                # Generate doctor notes for completed appointments
                doctor_notes = ""
                if status == 'completed':
                    doctor_notes_list = [
                        "Patient responded well to treatment. Prescribed medication and advised rest.",
                        "Routine checkup completed. All vitals normal. Advised healthy diet.",
                        "Follow-up appointment. Condition improving. Continue current medication.",
                        "Prescribed antibiotics. Advised to return if symptoms persist.",
                        "Referred to specialist for further evaluation.",
                        "Vaccination administered successfully. No adverse reactions.",
                        "Blood pressure slightly elevated. Recommended lifestyle changes.",
                        "Skin condition treated. Applied topical medication. Follow-up in 2 weeks.",
                        "Minor injury treated. Bandaged properly. Keep wound clean and dry.",
                        "Allergy consultation. Identified triggers. Prescribed antihistamine.",
                    ]
                    doctor_notes = random.choice(doctor_notes_list)

                # Create appointment
                appointment = Appointment(
                    doctor=doctor,
                    patient=patient,
                    appointment_date=random_date,
                    appointment_time=appointment_time,
                    status=status,
                    patient_notes=patient_notes,
                    doctor_notes=doctor_notes,
                    duration_minutes=random.choice([30, 45, 60]),
                    fee_charged=doctor.consultation_fee,
                    is_paid=status == 'completed' or random.choice([True, False]),
                    patient_email=patient.email
                )
                
                # Add flag for validation skip
                appointment._skip_date_validation = True

                # Save with validation skip for historical appointments
                appointment.save(skip_validation=True)
                appointments_created += 1

                if appointments_created % 10 == 0:
                    self.stdout.write(f'Created {appointments_created} appointments...')

            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'Error creating appointment: {str(e)}')
                )
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created {appointments_created} sample appointments'
            )
        )

        # Display summary
        self.display_appointment_summary()

    def display_appointment_summary(self):
        """Display a summary of created appointments"""
        self.stdout.write('\n=== APPOINTMENT SUMMARY ===')
        
        total = Appointment.objects.count()
        self.stdout.write(f'Total Appointments: {total}')
        
        # Status distribution
        for status_code, status_name in Appointment.STATUS_CHOICES:
            count = Appointment.objects.filter(status=status_code).count()
            percentage = (count / total * 100) if total > 0 else 0
            self.stdout.write(f'{status_name}: {count} ({percentage:.1f}%)')
        
        # Date distribution
        today = timezone.now().date()
        past = Appointment.objects.filter(appointment_date__lt=today).count()
        today_count = Appointment.objects.filter(appointment_date=today).count()
        future = Appointment.objects.filter(appointment_date__gt=today).count()
        
        self.stdout.write(f'\nDate Distribution:')
        self.stdout.write(f'Past: {past}')
        self.stdout.write(f'Today: {today_count}')
        self.stdout.write(f'Future: {future}')
        
        # Top doctors by appointments
        self.stdout.write(f'\nTop 5 Doctors by Appointments:')
        from django.db.models import Count
        top_doctors = Doctor.objects.annotate(
            appointment_count=Count('appointments')
        ).order_by('-appointment_count')[:5]
        
        for doctor in top_doctors:
            self.stdout.write(f'Dr. {doctor.first_name} {doctor.last_name}: {doctor.appointment_count} appointments')
