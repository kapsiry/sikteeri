from django.urls import re_path
import services.views

urlpatterns = [
    re_path(r'aliases/edit/(\d+)/$', services.views.alias_edit, name='alias_edit'),
    re_path(r'aliases/add_for_member/(\d+)/$', services.views.alias_add_for_member,
        name='services.views.alias_add_for_member'),
]