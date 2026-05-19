from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):
    """
    Allow access only to the object's owner or an admin user.
    The view must set `obj.user` as the ownership field.
    """

    def has_object_permission(self, request, view, obj):
        if request.user and request.user.is_staff:
            return True
        return getattr(obj, "user", None) == request.user
