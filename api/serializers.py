from rest_framework import serializers, mixins

from membership.models import Membership, Contact


class ContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Contact
        fields = ('first_name', 'last_name', 'given_names', 'country', 'sms', 'organization_name',
                  'phone', 'postal_code', 'post_office', 'homepage', 'email',
                  'street_address')


class MembershipSerializer(serializers.ModelSerializer, mixins.CreateModelMixin):

    class Meta:
        model = Membership
        read_only_fields = (
            'status', 'dissociated', 'dissociation_requested', 'locked', 'approved',
            'organization_registration_number', 'type', 'birth_year', 'person', 'organization'
        )
        fields = read_only_fields + (
            'municipality', 'public_memberlist', 'nationality',
            'tech_contact', 'billing_contact'
        )
