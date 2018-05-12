from django.conf.urls import url
import services.views

urlpatterns = [
    url(r'aliases/edit/(\d+)/$', services.views.alias_edit, name='alias_edit'),
    url(r'aliases/add_for_member/(\d+)/$', services.views.alias_add_for_member,
        name='services.views.alias_add_for_member'),
]