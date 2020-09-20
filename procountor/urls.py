from django.conf.urls import url

import procountor.views

urlpatterns = [
    url(r'^$', procountor.views.procountor_login, name='procountor_login'),
    url(r'^auth/$', procountor.views.procountor_login_return, name='procountor_login_return'),
]
