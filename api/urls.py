from django.conf.urls import url, include
from rest_framework import routers

import api
from api import views

router = routers.DefaultRouter()
#router.register(r'memberships', views.MembershipViewSet)
#router.register(r'contacts', views.ContactViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
    url(r'^framework/', include('rest_framework.urls', namespace='rest_framework')),
    # Piika views
    url(r'membership/(?P<pk>\d+)$', api.views.MemberInfoView.as_view({"get": "retrieve", "put": "update"}),
        name="api_member_info"),
    url(r'contact/(?P<pk>\d+)$', api.views.ContactInfoView.as_view({"get": "retrieve", "put": "update"}), name="api_contact_info"),
]
