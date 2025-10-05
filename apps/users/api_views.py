"""
API ViewSets for the users app.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from drf_spectacular.utils import extend_schema, extend_schema_view

from .models import UserProfile
from .serializers import (
    UserSerializer, UserProfileSerializer, UserProfileUpdateSerializer,
    UserRegistrationSerializer, ChangePasswordSerializer
)


@extend_schema_view(
    list=extend_schema(description="List all users (admin only)"),
    retrieve=extend_schema(description="Get user details"),
    create=extend_schema(description="Create a new user"),
    update=extend_schema(description="Update user information"),
    partial_update=extend_schema(description="Partially update user information"),
    destroy=extend_schema(description="Delete user account"),
)
class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action == 'create':
            # Allow anyone to create an account
            permission_classes = [permissions.AllowAny]
        elif self.action in ['list', 'destroy']:
            # Only admin can list all users or delete accounts
            permission_classes = [permissions.IsAdminUser]
        else:
            # Authenticated users can view/update their own data
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        if self.request.user.is_staff:
            return User.objects.all()
        else:
            # Regular users can only see their own data
            return User.objects.filter(id=self.request.user.id)
    
    def get_object(self):
        """Allow users to access their own profile via 'me' endpoint."""
        if self.kwargs.get('pk') == 'me':
            return self.request.user
        return super().get_object()
    
    @extend_schema(
        description="Get current user's profile",
        responses={200: UserSerializer}
    )
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Get current user's profile."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @extend_schema(
        description="Update current user's profile",
        request=UserProfileUpdateSerializer,
        responses={200: UserProfileUpdateSerializer}
    )
    @action(detail=False, methods=['patch'], permission_classes=[permissions.IsAuthenticated])
    def update_profile(self, request):
        """Update current user's profile information."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        description="Change user password",
        request=ChangePasswordSerializer,
        responses={200: {"description": "Password changed successfully"}}
    )
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_password(self, request):
        """Change user password."""
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    create=extend_schema(description="Register a new user account"),
)
class UserRegistrationViewSet(viewsets.GenericViewSet):
    """
    ViewSet for user registration.
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        description="Register a new user with profile information",
        responses={201: UserSerializer}
    )
    def create(self, request):
        """Register a new user."""
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            with transaction.atomic():
                user = serializer.save()
                
                # Return user data with profile
                user_serializer = UserSerializer(user)
                return Response(user_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    list=extend_schema(description="List user profiles (admin only)"),
    retrieve=extend_schema(description="Get user profile details"),
    update=extend_schema(description="Update user profile"),
    partial_update=extend_schema(description="Partially update user profile"),
)
class UserProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing user profiles.
    """
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Set permissions based on action."""
        if self.action == 'list':
            # Only admin can list all profiles
            permission_classes = [permissions.IsAdminUser]
        else:
            permission_classes = [permissions.IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Filter queryset based on user permissions."""
        if self.request.user.is_staff:
            return UserProfile.objects.all()
        else:
            # Regular users can only see their own profile
            return UserProfile.objects.filter(user=self.request.user)
    
    def get_object(self):
        """Allow users to access their own profile via 'me' endpoint."""
        if self.kwargs.get('pk') == 'me':
            profile, created = UserProfile.objects.get_or_create(user=self.request.user)
            return profile
        return super().get_object()
    
    def perform_create(self, serializer):
        """Set the user to the current user when creating a profile."""
        serializer.save(user=self.request.user)
    
    def perform_update(self, serializer):
        """Ensure users can only update their own profile."""
        if serializer.instance.user != self.request.user and not self.request.user.is_staff:
            raise permissions.PermissionDenied("You can only update your own profile.")
        serializer.save()


# Authentication Views (if needed for token-based auth)
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView

class LoginAPIView(APIView):
    """
    API view for user login.
    """
    permission_classes = [permissions.AllowAny]
    
    @extend_schema(
        description="Login user and return authentication token",
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string'},
                },
                'required': ['username', 'password']
            }
        },
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'token': {'type': 'string'},
                    'user': {
                        'type': 'object',
                        'description': 'User data'
                    }
                }
            }
        }
    )
    def post(self, request):
        """Authenticate user and return token."""
        username = request.data.get('username')
        password = request.data.get('password')
        
        if username and password:
            user = authenticate(username=username, password=password)
            if user and user.is_active:
                token, created = Token.objects.get_or_create(user=user)
                user_serializer = UserSerializer(user)
                return Response({
                    'token': token.key,
                    'user': user_serializer.data
                })
            else:
                return Response(
                    {'error': 'Invalid credentials'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            return Response(
                {'error': 'Username and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )


class LogoutAPIView(APIView):
    """
    API view for user logout.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = None  # No input required for logout
    
    @extend_schema(
        description="Logout user and delete authentication token",
        request=None,
        responses={200: {"description": "Successfully logged out"}}
    )
    def post(self, request):
        """Logout user by deleting their token."""
        try:
            token = Token.objects.get(user=request.user)
            token.delete()
            return Response({'message': 'Successfully logged out'})
        except Token.DoesNotExist:
            return Response({'message': 'User was not logged in'})


class UserStatsAPIView(APIView):
    """
    API view for user statistics.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        description="Get user's appointment and activity statistics",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'total_appointments': {'type': 'integer'},
                    'completed_appointments': {'type': 'integer'},
                    'upcoming_appointments': {'type': 'integer'},
                    'cancelled_appointments': {'type': 'integer'},
                    'profile_completion': {'type': 'number', 'format': 'float'},
                }
            }
        }
    )
    def get(self, request):
        """Get user statistics."""
        from apps.doctors.models import Appointment
        from django.utils import timezone
        
        user = request.user
        now = timezone.now()
        
        appointments = Appointment.objects.filter(patient=user)
        
        # Calculate profile completion percentage
        profile = getattr(user, 'userprofile', None)
        profile_completion = 0
        if profile:
            total_fields = 12  # Total important profile fields
            completed_fields = 0
            
            if profile.phone: completed_fields += 1
            if profile.date_of_birth: completed_fields += 1
            if profile.gender: completed_fields += 1
            if profile.address: completed_fields += 1
            if profile.city: completed_fields += 1
            if profile.state: completed_fields += 1
            if profile.country: completed_fields += 1
            if profile.postal_code: completed_fields += 1
            if profile.emergency_contact_name: completed_fields += 1
            if profile.emergency_contact_phone: completed_fields += 1
            if profile.profile_picture: completed_fields += 1
            if user.first_name and user.last_name: completed_fields += 1
            
            profile_completion = (completed_fields / total_fields) * 100
        
        stats = {
            'total_appointments': appointments.count(),
            'completed_appointments': appointments.filter(status='completed').count(),
            'upcoming_appointments': appointments.filter(
                status__in=['scheduled', 'confirmed'],
                appointment_date__gte=now.date()
            ).count(),
            'cancelled_appointments': appointments.filter(status='cancelled').count(),
            'profile_completion': round(profile_completion, 1),
        }
        
        return Response(stats)


class CurrentUserProfileAPIView(APIView):
    """
    API view for current user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        description="Get current user's profile information",
        responses={200: UserProfileSerializer}
    )
    def get(self, request):
        """Get current user's profile."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    
    @extend_schema(
        description="Update current user's profile information",
        request=UserProfileUpdateSerializer,
        responses={200: UserProfileUpdateSerializer}
    )
    def patch(self, request):
        """Update current user's profile."""
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        serializer = UserProfileUpdateSerializer(profile, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
