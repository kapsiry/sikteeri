import logging
logger = logging.getLogger("services.models")

from datetime import datetime
import unicodedata

from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError

def remove_accents(str):
    '''http://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string/517974#517974'''
    nkfd_form = unicodedata.normalize('NFKD', unicode(str))
    return u"".join([c for c in nkfd_form if not unicodedata.combining(c)])

def logging_log_change(sender, instance, created, **kwargs):
    operation = "created" if created else "modified"
    logger.info('%s %s: %s' % (sender.__name__, operation, repr(instance)))

def _get_logs(self):
    '''Gets the log entries related to this object.
    Getter to be used as property instead of GenericRelation'''
    my_class = self.__class__
    ct = ContentType.objects.get_for_model(my_class)
    object_logs = ct.logentry_set.filter(object_id=self.id)
    return object_logs

class Service(models.Model):
    class Meta:
        permissions = (
            ("can_manage_services", "Can manage member services"),
        )
    """
    Services such as UNIX account, email aliases, vhosts etc.
    """
    servicetype = models.ForeignKey('ServiceType', verbose_name=_('Service type'))
    alias = models.ForeignKey('Alias', verbose_name=_('Related alias'), null=True)
    owner = models.ForeignKey('membership.Membership', verbose_name=_('Service owner'), null=True)
    data = models.CharField(max_length=256, verbose_name=_('Service specific data'), blank=True)

    def __unicode__(self):
        if self.alias:
            return "%s %s" % (self.servicetype, self.alias)
        else:
            return unicode(self.servicetype)

    def __str__(self):
        return unicode(self).encode('ASCII', 'backslashreplace')

class ServiceType(models.Model):
    class Meta:
        permissions = (
            ("can_manage_servicetypes", "Can manage available service types"),
        )
    """
    Available service types
    """
    servicetype = models.CharField(max_length=64, verbose_name=_('Service type'), unique=True)

    def __unicode__(self):
        return unicode(self.servicetype)

    def __str__(self):
        return unicode(self).encode('ASCII', 'backslashreplace')

class Alias(models.Model):
    owner = models.ForeignKey('membership.Membership', verbose_name=_('Alias owner'))
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Alias name'))
    account = models.BooleanField(default=False, verbose_name=_('Is UNIX account'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))
    expiration_date = models.DateTimeField(blank=True, null=True, verbose_name=_('Alias expiration date'))
    logs = property(_get_logs)

    class Meta:
        permissions = (
            ("manage_aliases", "Can manage aliases"),
        )
        ordering = ["name"]
        verbose_name_plural = "aliases"

    def expire(self, time=None):
        if time == None:
            time = datetime.now()
        self.expiration_date = time
        self.save()

    def clean(self):
        self.name = self.name.strip()

    def is_valid(self):
        expiration = self.expiration_date
        if not expiration or expiration > datetime.now():
            return True
        else:
            return False

    @classmethod
    def email_forwards(cls, membership=None, first_name=None, last_name=None,
                       given_names=None):
        "Returns a list of available email forward permutations."
        if membership:
            first_name = remove_accents(membership.person.first_name.lower())
            last_name = remove_accents(membership.person.last_name.lower())
            given_names = remove_accents(membership.person.given_names.lower())
        else:
            first_name = remove_accents(first_name.lower())
            last_name = remove_accents(last_name.lower())
            given_names = remove_accents(given_names.lower())

        permutations = []

        permutations.append(first_name + "." + last_name)
        permutations.append(last_name + "." + first_name)

        non_first_names = []
        initials = []
        for n in given_names.split(" "):
            if n != first_name:
                non_first_names.append(n)
                initials.append(n)

        all_initials_name = []
        for i in initials:
            permutations.append(first_name + "." + i + "." + last_name)
            permutations.append(i + "." + first_name + "." + last_name)
            all_initials_name.append(i)

        all_initials_name.append(last_name)
        permutations.append(".".join(all_initials_name))

        return [perm for perm in permutations
                if cls.objects.filter(name__iexact=perm).count() == 0]

    @classmethod
    def unix_logins(cls, membership=None, first_name=None, last_name=None,
                    given_names=None):
        "Returns a list of available user login names."
        if membership:
            first_name = remove_accents(membership.person.first_name.lower())
            last_name = remove_accents(membership.person.last_name.lower())
            given_names = remove_accents(membership.person.given_names.lower())
        else:
            first_name = remove_accents(first_name.lower())
            last_name = remove_accents(last_name.lower())
            given_names = remove_accents(given_names.lower())

        permutations = []

        permutations.append(last_name)
        permutations.append(first_name)
        permutations.append(first_name + last_name)
        permutations.append(last_name + first_name)

        non_first_names = []
        initials = []
        for n in given_names.split(" "):
            if n != first_name:
                non_first_names.append(n)
                initials.append(n)

        permutations.append("".join(initials) + last_name[0])
        permutations.append("".join(initials) + last_name)

        for initial in initials:
            permutations.append(initial + last_name)

        return [perm for perm in permutations
                if cls.objects.filter(name__iexact=perm).count() == 0]

    def save(self,*args,**kwargs):
        try:
            self.full_clean()
        except ValidationError as e:
            raise e

        super(Alias, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

def valid_aliases(owner):
    '''Builds a queryset of all valid aliases'''
    no_expire = Q(expiration_date=None)
    not_expired = Q(expiration_date__lt=datetime.now())
    return Alias.objects.filter(no_expire | not_expired).filter(owner=owner)


models.signals.post_save.connect(logging_log_change, sender=Alias)
models.signals.post_save.connect(logging_log_change, sender=Service)
