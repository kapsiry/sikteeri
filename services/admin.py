from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.translation import ugettext_lazy as _
from services.models import Service, ServiceType, Alias


# See
# <http://docs.djangoproject.com/en/dev/ref/contrib/admin/#django.contrib.admin.ModelAdmin.list_filter>
# for documentation
class StartsWithListFilter(SimpleListFilter):
    title = _('Starts with')

    parameter_name = 'starts_with'

    def lookups(self, request, model_admin):
        def first_two(s):
            s = str(s)
            if len(s) < 2:
                return s
            else:
                return s[:2]

        prefixes = [first_two(alias.name)
                    for alias in model_admin.model.objects.only('name')]

        prefixes = sorted(set(prefixes))

        return [(prefix, prefix) for prefix in prefixes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(name__istartswith=self.value())
        else:
            return queryset


class AliasAdmin(admin.ModelAdmin):
    raw_id_fields = ['owner']
    list_filter = (StartsWithListFilter,)


admin.site.register(Service)
admin.site.register(ServiceType)
admin.site.register(Alias, AliasAdmin)
