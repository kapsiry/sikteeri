from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, get_object_or_404

# Create your views here.
from rest_framework import viewsets

from api import serializers
from membership.models import Membership, Contact
from membership.utils import log_change


class MemberInfoView(viewsets.ModelViewSet):
    queryset = Membership.objects.all()  # Required for DjangoModelPermissions
    serializer_class = serializers.MembershipSerializer

    def perform_update(self, serializer, *args, **kwargs):
        print("perform update called")
        before = Membership.objects.get(id=serializer.instance.pk)
        serialized_before = self.serializer_class(before)
        serializer.save()
        log_change(before, self.request.user, serialized_before.data, serializer.data)


class ContactInfoView(viewsets.ModelViewSet):
    queryset = Contact.objects.all()  # Required for DjangoModelPermissions
    serializer_class = serializers.ContactSerializer

    def perform_update(self, serializer, *args, **kwargs):
        print("perform update called")
        before = Contact.objects.get(id=serializer.instance.pk)
        serialized_before = self.serializer_class(before)
        serializer.save()
        log_change(before, self.request.user, serialized_before.data, serializer.data)
