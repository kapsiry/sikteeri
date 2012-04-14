from django.contrib import admin
from services.models import Service, ServiceType, Alias

admin.site.register(Service)
admin.site.register(ServiceType)
admin.site.register(Alias)
