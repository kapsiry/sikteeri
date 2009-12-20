from django.contrib.contenttypes.models import ContentType
from django.utils.encoding import force_unicode


from membership.models import BillingCycle, Bill

# http://code.activestate.com/recipes/576644/

KEYNOTFOUNDIN1 = '<KEYNOTFOUNDIN1>'       # KeyNotFound for dictDiff
KEYNOTFOUNDIN2 = '<KEYNOTFOUNDIN2>'       # KeyNotFound for dictDiff

def dict_diff(first, second):
    """ Return a dict of keys that differ with another config object.  If a value is
        not found in one fo the configs, it will be represented by KEYNOTFOUND.
        @param first:   Fist dictionary to diff.
        @param second:  Second dicationary to diff.
        @return diff:   Dict of Key => (first.val, second.val)
    """
    diff = {}
    sd1 = set(first)
    sd2 = set(second)
    #Keys missing in the second dict
    for key in sd1.difference(sd2):
        diff[key] = KEYNOTFOUNDIN2
    #Keys missing in the first dict
    for key in sd2.difference(sd1):
        diff[key] = KEYNOTFOUNDIN1
    #Check for differences
    for key in sd1.intersection(sd2):
        if first[key] != second[key]:
            diff[key] = (first[key], second[key])    
    return diff


def new_cycle(membership):
    old_cycle = membership.billingcycle_set.order_by('-end')[0]
    billing_cycle = BillingCycle(membership=membership, start=old_cycle.end)
    billing_cycle.save() # Creating an instance does not touch db and we need and id for the Bill
    bill = Bill(cycle=billing_cycle)
    bill.save()
    bill.send_as_email()

def sendreminder(membership): # XXX Test if cycle is paid?
    billing_cycle = membership.billingcycle_set.order_by('-end')[0]
    bill = Bill(cycle=billing_cycle)
    bill.save()
    bill.send_as_email()

def disable_member(membership): 
    pass # XXX

def log_change(object, user, before=None, after=None, change_message=None):
    if not change_message:
        if before and after:
            change_message  = repr(dict_diff(before, after)) # XXX
        else:
            change_message = "Some changes were made"
    from django.contrib.admin.models import LogEntry, CHANGE
    LogEntry.objects.log_action(
        user_id         = user.pk,
        content_type_id = ContentType.objects.get_for_model(object).pk,
        object_id       = object.pk,
        object_repr     = force_unicode(object),
        action_flag     = CHANGE,
        change_message  = change_message
    )
