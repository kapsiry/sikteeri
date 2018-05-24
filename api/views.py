from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, get_object_or_404

# Create your views here.
from rest_framework import viewsets, permissions

from api import serializers
from membership.models import Membership, Contact
from membership.utils import log_change


class HasPermissionToMember(permissions.BasePermission):
    """
    Implement custom permission checks
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user.has_perm('membership.read_members')
        elif request.method in ['POST', 'PUT']:
            return request.user.has_perm('membership.manage_members')
        # Disable other methods
        return False


class MemberInfoView(viewsets.ModelViewSet):
    """
    Membership general info
    """
    queryset = Membership.objects.all()  # Required for DjangoModelPermissions
    serializer_class = serializers.MembershipSerializer
    permission_classes = (permissions.DjangoModelPermissions, HasPermissionToMember)

    def perform_update(self, serializer, *args, **kwargs):
        """
        Update and log changes
        """
        before = Membership.objects.get(id=serializer.instance.pk)
        serialized_before = self.serializer_class(before)
        serializer.save()
        log_change(before, self.request.user, serialized_before.data, serializer.data)


class ContactInfoView(viewsets.ModelViewSet):
    """
    Membership contact info
    """
    queryset = Contact.objects.all()  # Required for DjangoModelPermissions
    serializer_class = serializers.ContactSerializer
    permission_classes = (permissions.DjangoModelPermissions, HasPermissionToMember)

    def perform_update(self, serializer, *args, **kwargs):
        """
        Update and log changes
        """
        before = Contact.objects.get(id=serializer.instance.pk)
        serialized_before = self.serializer_class(before)
        serializer.save()
        log_change(before, self.request.user, serialized_before.data, serializer.data)
