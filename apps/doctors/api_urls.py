"""
API URL configuration for doctors app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.response import Response
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema
from drf_spectacular.openapi import OpenApiResponse
from . import api_views
from .models import Doctor

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'doctors', api_views.DoctorViewSet, basename='doctor')
router.register(r'appointments', api_views.AppointmentViewSet, basename='appointment')
router.register(r'availability', api_views.DoctorAvailabilityViewSet, basename='availability')
router.register(r'reviews', api_views.ReviewViewSet, basename='review')

@extend_schema(
    responses={
        200: OpenApiResponse(
            description="List of available doctor specialties",
            response={'specialties': ['string']}
        )
    }
)
@api_view(['GET'])
def specialties_list(request):
    """Get list of available doctor specialties."""
    specialties = [choice[0] for choice in Doctor.SPECIALTIES]
    return Response({'specialties': specialties})

app_name = 'doctors_api'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Additional endpoints
    path('specialties/', specialties_list, name='specialties'),
]
