"""
Management command to optimize database performance.

This command performs various database optimization tasks including:
- Updating doctor statistics
- Warming up cache
- Analyzing slow queries
- Generating performance reports
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from apps.doctors.db_optimizations import DatabaseOptimizer, PerformanceMonitor
from apps.doctors.models import Doctor
import time


class Command(BaseCommand):
    help = 'Optimize database performance and update statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            type=str,
            choices=['all', 'stats', 'cache', 'analyze'],
            default='all',
            help='Specific optimization task to run'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        start_time = time.time()
        task = options['task']
        verbose = options['verbose']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting database optimization (task: {task})')
        )

        try:
            if task in ['all', 'stats']:
                self.update_statistics(verbose)
            
            if task in ['all', 'cache']:
                self.warm_cache(verbose)
            
            if task in ['all', 'analyze']:
                self.analyze_performance(verbose)
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Database optimization completed successfully in {duration:.2f} seconds'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Optimization failed: {str(e)}')
            )
            raise CommandError(f'Database optimization failed: {str(e)}')

    def update_statistics(self, verbose=False):
        """Update doctor statistics and ratings."""
        if verbose:
            self.stdout.write('Updating doctor statistics...')
        
        try:
            DatabaseOptimizer.update_doctor_statistics()
            
            # Get counts for reporting
            total_doctors = Doctor.objects.count()
            verified_doctors = Doctor.objects.filter(is_verified=True).count()
            available_doctors = Doctor.objects.filter(is_available=True).count()
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Updated statistics for {total_doctors} doctors '
                    f'({verified_doctors} verified, {available_doctors} available)'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to update statistics: {str(e)}')
            )
            raise

    def warm_cache(self, verbose=False):
        """Warm up the cache with frequently accessed data."""
        if verbose:
            self.stdout.write('Warming up cache...')
        
        try:
            # Clear existing cache first
            cache.clear()
            
            DatabaseOptimizer.warm_up_cache()
            
            # Cache additional data
            self._cache_popular_searches()
            
            self.stdout.write(
                self.style.SUCCESS('✓ Cache warmed up successfully')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to warm cache: {str(e)}')
            )
            raise

    def _cache_popular_searches(self):
        """Cache results for popular search queries."""
        popular_searches = [
            {'specialty': 'cardiology'},
            {'specialty': 'general_medicine'},
            {'specialty': 'pediatrics'},
            {'city': 'Delhi'},
            {'city': 'Mumbai'},
            {'city': 'Bangalore'},
        ]
        
        for search in popular_searches:
            # Simple search implementation for caching
            qs = Doctor.objects.filter(is_available=True)
            if search.get('specialty'):
                qs = qs.filter(specialty=search['specialty'])
            if search.get('city'):
                qs = qs.filter(city__icontains=search['city'])
            
            results = list(qs[:20])
            cache_key = f"popular_search_{hash(str(search))}"
            cache.set(cache_key, results, 900)  # 15 minutes
            
    def analyze_performance(self, verbose=False):
        """Analyze database performance and log findings."""
        if verbose:
            self.stdout.write('Analyzing database performance...')
        
        try:
            # Clear connection queries to start fresh
            connection.queries_log.clear()
            
            # Perform some common operations to analyze
            self._perform_sample_queries()
            
            # Get performance statistics
            stats = PerformanceMonitor.get_query_stats()
            
            self.stdout.write('Performance Analysis Results:')
            self.stdout.write(f'  Total Queries: {stats["total_queries"]}')
            self.stdout.write(f'  Total Time: {stats["total_time"]:.3f}s')
            self.stdout.write(f'  Slow Queries: {stats["slow_queries"]}')
            
            if stats["slow_queries"] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'⚠ Found {stats["slow_queries"]} slow queries - check logs for details'
                    )
                )
                PerformanceMonitor.log_slow_queries()
            else:
                self.stdout.write(
                    self.style.SUCCESS('✓ No slow queries detected')
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to analyze performance: {str(e)}')
            )
            raise

    def _perform_sample_queries(self):
        """Perform sample queries to test performance."""
        # Test different query patterns
        
        # 1. Simple filtering
        Doctor.objects.filter(is_available=True)[:10]
        
        # 2. Complex search with joins
        Doctor.objects.filter(is_available=True).select_related('user')[:5]
        
        # 3. Aggregation queries
        from django.db.models import Count, Avg
        Doctor.objects.aggregate(
            total=Count('id'),
            avg_rating=Avg('average_rating')
        )
        
        # 4. Search with multiple filters
        Doctor.objects.filter(
            specialty='cardiology',
            city__icontains='Delhi',
            experience_years__gte=5,
            is_available=True
        )[:10]
        
        # 5. Related object queries
        doctors = Doctor.objects.select_related('user').prefetch_related(
            'reviews', 'availability_slots'
        )[:5]
        
        for doctor in doctors:
            # Force evaluation of related objects
            list(doctor.reviews.all())
            list(doctor.availability_slots.all())
