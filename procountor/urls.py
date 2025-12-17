from django.urls import re_path

import procountor.views

urlpatterns = [
    re_path(r'^$', procountor.views.procountor_login, name='procountor_login'),
    re_path(r'^auth/$', procountor.views.procountor_login_return, name='procountor_login_return'),
]
