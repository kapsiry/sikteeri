from membership.models import Membership


def find_memberid(contact_id):
    # Is there better way to find a memberid?
    try:
        return Membership.objects.get(person_id=contact_id).id
    except Membership.DoesNotExist:
        pass
    try:
        return Membership.objects.get(organization_id=contact_id).id
    except Membership.DoesNotExist:
        pass
    try:
        return Membership.objects.get(billing_contact_id=contact_id).id
    except Membership.DoesNotExist:
        pass
    try:
        return Membership.objects.get(tech_contact_id=contact_id).id
    except Membership.DoesNotExist:
         return None