from rest_framework import permissions
from rest_framework.permissions import BasePermission



class IsOwnerOrReadOnly(BasePermission):
    """
    Custom permission to allow users to edit their own object.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        return obj.user == request.user


class IsAuthenticatedAndVerified(BasePermission):

    def has_permission(self, request, view):
        # Check if user is authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user's email is verified
        if not hasattr(request.user, 'email_verified') or not request.user.email_verified:
            return False
            
        return True




def ConstantPermission(*groups):
    class _GroupPermission(BasePermission):
        message = "You do not have permission to access this resource."

        def has_permission(self, request, view):
            user = request.user

            if not user or not user.is_authenticated:
                return False

            return user.groups.filter(name__in=groups).exists()

    return _GroupPermission