# This is shared between management commands and views
from membership.models import Membership


def public_memberlist_data():
    """Get the membership counts and data for public memberlist."""
    mship = Membership.objects.filter(status__exact='A', id__gt=0)
    membership_count = mship.count()
    public_members = mship.filter(public_memberlist="True") \
                          .order_by('person__last_name',
                                    'person__first_name')
    public_membership_count = public_members.count()
    return dict(membership_count=membership_count,
                public_membership_count=public_membership_count,
                public_members=public_members)

