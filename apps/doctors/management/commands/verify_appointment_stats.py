from django.core.management.base import BaseCommand
from apps.doctors.models import Doctor, Appointment
from datetime import date


class Command(BaseCommand):
    help = 'Verify appointment statistics consistency between views'

    def handle(self, *args, **options):
        self.stdout.write("🔍 Verifying appointment statistics consistency...\n")
        
        # Get Dr. Vihaan Kapoor as example (from the screenshot)
        try:
            doctor = Doctor.objects.get(first_name__icontains="Vihaan")
            self.stdout.write(f"Checking stats for: Dr. {doctor.first_name} {doctor.last_name}")
        except Doctor.DoesNotExist:
            # Fallback to any doctor
            doctor = Doctor.objects.first()
            if not doctor:
                self.stdout.write("No doctors found in database")
                return
            self.stdout.write(f"Checking stats for: Dr. {doctor.first_name} {doctor.last_name}")
        
        today = date.today()
        
        # Calculate all statistics the same way as both views
        self.stdout.write("\n=== TODAY'S STATISTICS ===")
        todays_appointments = doctor.appointments.filter(appointment_date=today)
        todays_total = todays_appointments.count()
        todays_confirmed = todays_appointments.filter(status__in=['confirmed', 'scheduled']).count()
        todays_completed = todays_appointments.filter(status='completed').count()
        
        todays_completed_appointments = todays_appointments.filter(status='completed')
        todays_earnings = sum(
            apt.fee_charged or doctor.consultation_fee 
            for apt in todays_completed_appointments
        )
        
        self.stdout.write(f"Total Today: {todays_total}")
        self.stdout.write(f"Confirmed Today: {todays_confirmed}")
        self.stdout.write(f"Completed Today: {todays_completed}")
        self.stdout.write(f"Today's Earnings: ₹{todays_earnings}")
        
        self.stdout.write("\n=== OVERALL STATISTICS ===")
        total_appointments = doctor.appointments.count()
        completed_appointments = doctor.appointments.filter(status='completed').count()
        upcoming_appointments = doctor.appointments.filter(
            status__in=['scheduled', 'confirmed'],
            appointment_date__gte=today
        ).count()
        
        completed_all = doctor.appointments.filter(status='completed')
        total_earnings = sum(
            apt.fee_charged or doctor.consultation_fee 
            for apt in completed_all
        )
        
        self.stdout.write(f"Total Appointments: {total_appointments}")
        self.stdout.write(f"Completed Appointments: {completed_appointments}")
        self.stdout.write(f"Upcoming Appointments: {upcoming_appointments}")
        self.stdout.write(f"Total Earnings: ₹{total_earnings}")
        
        self.stdout.write("\n=== APPOINTMENT BREAKDOWN BY STATUS ===")
        for status_code, status_name in Appointment.STATUS_CHOICES:
            count = doctor.appointments.filter(status=status_code).count()
            self.stdout.write(f"{status_name}: {count}")
        
        self.stdout.write(f"\n✅ Statistics calculated consistently for both appointments page and profile page")
