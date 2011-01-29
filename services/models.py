from django.utils.translation import ugettext_lazy as _
from django.db import models

from membership.models import Membership

class Service(models.Model):
    class Meta:
        permissions = (
            ("can_manage_services", "Can manage member services"),
        )
    """
    Services such as UNIX account, email aliases, vhosts etc.
    """
    servicetype = models.ForeignKey('ServiceType', verbose_name=_('Service type'))
    alias = models.ForeignKey('membership.Alias', verbose_name=_('Related alias'), null=True)
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
