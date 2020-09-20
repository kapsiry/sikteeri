from django.db import models
from django.utils.translation import ugettext_lazy as _


class APIToken(models.Model):
    """
    Object for Procountor API token
    There should be only one token.
    """
    class Meta:
        permissions = (
            ("can_add_procountor_token", "Can add Procountor token"),
        )

    api_key = models.CharField(max_length=1024)
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('last changed'))

    @classmethod
    def current(cls):
        object = APIToken.objects.first()
        if not object:
            return None
        return object.api_key
