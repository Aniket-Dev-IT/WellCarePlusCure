"""
API URL configuration for users app.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'users', api_views.UserViewSet, basename='user')
router.register(r'register', api_views.UserRegistrationViewSet, basename='register')
router.register(r'profiles', api_views.UserProfileViewSet, basename='userprofile')

app_name = 'users_api'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),
    
    # Authentication endpoints
    path('auth/login/', api_views.LoginAPIView.as_view(), name='login'),
    path('auth/logout/', api_views.LogoutAPIView.as_view(), name='logout'),
    
    # User statistics
    path('stats/', api_views.UserStatsAPIView.as_view(), name='stats'),
    
    # Current user profile
    path('profile/', api_views.CurrentUserProfileAPIView.as_view(), name='profile'),
]
