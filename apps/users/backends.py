"""
Custom authentication backends for the users app.

This module provides authentication backends that allow users to login
with either their username or email address.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Custom authentication backend that allows users to login using either
    their username or email address.
    
    This backend extends Django's ModelBackend to support both username
    and email authentication while maintaining all other Django authentication
    features like permissions, groups, etc.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Authenticate a user using either username or email.
        
        Args:
            request: The current request object
            username: Username or email address provided by the user
            password: Password provided by the user
            **kwargs: Additional keyword arguments
            
        Returns:
            User object if authentication is successful, None otherwise
        """
        if username is None or password is None:
            return None
            
        try:
            # Try to find the user by username or email
            user = User.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a non-existing user
            User().set_password(password)
            return None
        except User.MultipleObjectsReturned:
            # If multiple users have the same email, fall back to username only
            try:
                user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                return None
        
        # Check the password and return the user if valid
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
    
    def get_user(self, user_id):
        """
        Get a user by their ID.
        
        This method is required by Django's authentication framework.
        """
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
        
        return user if self.user_can_authenticate(user) else None