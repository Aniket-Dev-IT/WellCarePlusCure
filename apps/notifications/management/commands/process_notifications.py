from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.notifications.services import NotificationService
from apps.notifications.models import NotificationQueue
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process pending notifications in the queue'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--max-notifications',
            type=int,
            default=100,
            help='Maximum number of notifications to process'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing'
        )
    
    def handle(self, *args, **options):
        max_notifications = options['max_notifications']
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Starting notification processing (max: {max_notifications}, dry_run: {dry_run})'
            )
        )
        
        if dry_run:
            # Show what would be processed
            pending_count = NotificationQueue.objects.filter(
                processed=False,
                next_attempt_at__lte=timezone.now()
            ).count()
            
            self.stdout.write(
                f'Would process {min(pending_count, max_notifications)} notifications'
            )
            
            # Show some details about pending notifications
            pending_notifications = NotificationQueue.objects.filter(
                processed=False,
                next_attempt_at__lte=timezone.now()
            ).select_related('notification')[:10]
            
            if pending_notifications:
                self.stdout.write('\nPending notifications (first 10):')
                for queue_item in pending_notifications:
                    self.stdout.write(
                        f'  - {queue_item.notification.title} '
                        f'(attempts: {queue_item.attempts}/{queue_item.max_attempts})'
                    )
            
            return
        
        # Process notifications
        service = NotificationService()
        
        try:
            processed_count = service.process_queue(max_notifications=max_notifications)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed {processed_count} notifications'
                )
            )
            
            # Show remaining queue status
            remaining_pending = NotificationQueue.objects.filter(
                processed=False
            ).count()
            
            failed_attempts = NotificationQueue.objects.filter(
                processed=False,
                attempts__gte=3
            ).count()
            
            if remaining_pending > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'{remaining_pending} notifications still pending '
                        f'({failed_attempts} with failed attempts)'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('All notifications processed!')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing notifications: {str(e)}')
            )
            logger.error(f'Notification processing error: {str(e)}')
            raise
