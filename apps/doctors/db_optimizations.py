"""
Database optimization utilities for the doctors app.

This module provides custom managers, querysets, and caching utilities
to improve database performance and reduce query times.
"""

from django.db import models
from django.core.cache import cache
from django.db.models import Count, Avg, Q, Prefetch
from django.utils import timezone
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class OptimizedDoctorQuerySet(models.QuerySet):
    """
    Custom QuerySet for Doctor model with performance optimizations.
    """
    
    def with_stats(self):
        """
        Annotate doctors with calculated statistics.
        """
        return self.annotate(
            review_count=Count('reviews', filter=Q(reviews__is_approved=True)),
            avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
            appointment_count=Count('appointments'),
            active_appointments=Count('appointments', filter=Q(appointments__status__in=['scheduled', 'confirmed']))
        )
    
    def available_with_slots(self):
        """
        Get available doctors with their availability slots.
        """
        return self.filter(
            is_available=True
        ).prefetch_related(
            Prefetch(
                'availability_slots',
                queryset=self.model.availability_slots.related.related_model.objects.filter(
                    is_active=True
                ).order_by('day_of_week', 'start_time')
            )
        )
    
    def highly_rated(self, min_rating=4.0):
        """
        Get doctors with high ratings.
        """
        return self.filter(
            average_rating__gte=min_rating,
            total_reviews__gte=5
        )
    
    def by_specialty_and_location(self, specialty=None, city=None, state=None):
        """
        Filter doctors by specialty and location efficiently.
        """
        qs = self
        if specialty:
            qs = qs.filter(specialty=specialty)
        if city:
            qs = qs.filter(city__icontains=city)
        if state:
            qs = qs.filter(state__icontains=state)
        return qs
    
    def search_optimized(self, query):
        """
        Perform optimized full-text search.
        """
        if not query:
            return self
            
        # Use database-specific full-text search if available
        return self.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(qualification__icontains=query) |
            Q(bio__icontains=query) |
            Q(clinic_name__icontains=query) |
            Q(specializations__name__icontains=query)
        ).distinct()


class OptimizedDoctorManager(models.Manager):
    """
    Custom manager for Doctor model with performance optimizations.
    """
    
    def get_queryset(self):
        return OptimizedDoctorQuerySet(self.model, using=self._db)
    
    def available_doctors(self):
        """
        Get all available doctors with optimized queries.
        """
        return self.get_queryset().filter(
            is_available=True
        ).select_related('user').with_stats()
    
    def featured_doctors(self, limit=6):
        """
        Get featured doctors based on ratings and reviews.
        """
        cache_key = f'featured_doctors_{limit}'
        doctors = cache.get(cache_key)
        
        if doctors is None:
            doctors = list(
                self.get_queryset()
                .available_doctors()
                .highly_rated()
                .order_by('-average_rating', '-total_reviews')[:limit]
            )
            # Cache for 1 hour
            cache.set(cache_key, doctors, 3600)
            logger.info(f'Cached {len(doctors)} featured doctors')
        
        return doctors
    
    def search_doctors(self, **filters):
        """
        Comprehensive doctor search with caching.
        """
        cache_key = f"doctor_search_{hash(str(sorted(filters.items())))}"
        results = cache.get(cache_key)
        
        if results is None:
            qs = self.get_queryset().available_doctors()
            
            # Apply filters
            if filters.get('specialty'):
                qs = qs.filter(specialty=filters['specialty'])
            if filters.get('city'):
                qs = qs.filter(city__icontains=filters['city'])
            if filters.get('state'):
                qs = qs.filter(state__icontains=filters['state'])
            if filters.get('search_query'):
                qs = qs.search_optimized(filters['search_query'])
            if filters.get('min_experience'):
                qs = qs.filter(experience_years__gte=filters['min_experience'])
            if filters.get('max_fee'):
                qs = qs.filter(consultation_fee__lte=filters['max_fee'])
            if filters.get('rating_min'):
                qs = qs.filter(average_rating__gte=filters['rating_min'])
            if filters.get('verified_only'):
                qs = qs.filter(is_verified=True)
            
            results = list(qs.order_by('-average_rating'))
            # Cache for 15 minutes
            cache.set(cache_key, results, 900)
        
        return results


class CachingMixin:
    """
    Mixin to provide caching functionality for models.
    """
    
    @classmethod
    def get_cache_key(cls, *args):
        """Generate cache key for the model."""
        return f"{cls._meta.label_lower}_{':'.join(map(str, args))}"
    
    def invalidate_cache(self, *patterns):
        """Invalidate cache keys matching patterns."""
        for pattern in patterns:
            cache_key = self.get_cache_key(pattern, self.pk)
            cache.delete(cache_key)


class DatabaseOptimizer:
    """
    Utility class for database optimization operations.
    """
    
    @staticmethod
    def warm_up_cache():
        """
        Pre-populate cache with frequently accessed data.
        """
        from .models import Doctor
        
        logger.info("Warming up cache...")
        
        # Cache featured doctors
        featured_doctors = list(
            Doctor.objects.filter(
                is_available=True,
                average_rating__gte=4.0,
                total_reviews__gte=5
            ).order_by('-average_rating', '-total_reviews')[:6]
        )
        cache.set('featured_doctors_6', featured_doctors, 3600)
        
        # Cache doctors by popular specialties
        popular_specialties = ['cardiology', 'general_medicine', 'pediatrics', 'dermatology']
        for specialty in popular_specialties:
            cache_key = f'doctors_by_specialty_{specialty}'
            doctors = list(
                Doctor.objects.filter(
                    specialty=specialty, 
                    is_available=True
                ).select_related('user')[:10]
            )
            cache.set(cache_key, doctors, 1800)  # 30 minutes
        
        # Cache doctor count by city
        from django.db.models import Count
        city_stats = Doctor.objects.values('city').annotate(
            count=Count('id')
        ).order_by('-count')[:20]
        cache.set('doctor_count_by_city', list(city_stats), 3600)
        
        logger.info("Cache warm-up completed")
    
    @staticmethod
    def update_doctor_statistics():
        """
        Batch update doctor statistics to avoid N+1 queries.
        """
        from .models import Doctor
        from django.db.models import Avg, Count
        
        logger.info("Updating doctor statistics...")
        
        # Update in batches to avoid memory issues
        batch_size = 100
        doctors = Doctor.objects.all()
        total = doctors.count()
        
        for i in range(0, total, batch_size):
            batch = doctors[i:i + batch_size]
            
            for doctor in batch:
                # Get review statistics
                review_stats = doctor.reviews.filter(is_approved=True).aggregate(
                    avg_rating=Avg('rating'),
                    total_reviews=Count('id')
                )
                
                # Update fields
                doctor.average_rating = review_stats['avg_rating'] or 0.00
                doctor.total_reviews = review_stats['total_reviews']
                doctor.total_patients = doctor.appointments.values('patient').distinct().count()
            
            # Bulk update
            Doctor.objects.bulk_update(
                batch, 
                ['average_rating', 'total_reviews', 'total_patients']
            )
            
            logger.info(f"Updated statistics for {i + len(batch)}/{total} doctors")
    
    @staticmethod
    def optimize_database():
        """
        Run database optimization tasks.
        """
        logger.info("Starting database optimization...")
        
        # Update statistics
        DatabaseOptimizer.update_doctor_statistics()
        
        # Warm up cache
        DatabaseOptimizer.warm_up_cache()
        
        # Clean up old cache entries (if needed)
        DatabaseOptimizer.cleanup_expired_cache()
        
        logger.info("Database optimization completed")
    
    @staticmethod
    def cleanup_expired_cache():
        """
        Clean up expired cache entries.
        """
        # Django's cache backend handles this automatically,
        # but you can implement custom cleanup logic here
        pass


class QueryCounter:
    """
    Context manager to count database queries for performance monitoring.
    """
    
    def __init__(self, description=""):
        self.description = description
        self.initial_queries = 0
        self.final_queries = 0
    
    def __enter__(self):
        from django.db import connection
        self.initial_queries = len(connection.queries)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        from django.db import connection
        self.final_queries = len(connection.queries)
        query_count = self.final_queries - self.initial_queries
        
        logger.info(
            f"Query count{' for ' + self.description if self.description else ''}: {query_count}"
        )
        
        if query_count > 10:
            logger.warning(f"High query count detected: {query_count}")


def cache_doctor_search_results(view_func):
    """
    Decorator to cache doctor search results.
    """
    def wrapper(*args, **kwargs):
        # Generate cache key from request parameters
        request = args[0] if args else None
        if request and hasattr(request, 'GET'):
            cache_key = f"search_results_{hash(str(sorted(request.GET.items())))}"
            results = cache.get(cache_key)
            
            if results is None:
                results = view_func(*args, **kwargs)
                cache.set(cache_key, results, 600)  # 10 minutes
        else:
            results = view_func(*args, **kwargs)
        
        return results
    return wrapper


# Performance monitoring utilities
class PerformanceMonitor:
    """
    Monitor database performance and slow queries.
    """
    
    @staticmethod
    def log_slow_queries():
        """
        Log slow database queries for analysis.
        """
        from django.db import connection
        
        for query in connection.queries:
            time = float(query['time'])
            if time > 0.1:  # Log queries taking more than 100ms
                logger.warning(f"Slow query ({time}s): {query['sql'][:200]}...")
    
    @staticmethod
    def get_query_stats():
        """
        Get database query statistics.
        """
        from django.db import connection
        
        return {
            'total_queries': len(connection.queries),
            'total_time': sum(float(q['time']) for q in connection.queries),
            'slow_queries': len([q for q in connection.queries if float(q['time']) > 0.1])
        }
