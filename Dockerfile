FROM python:2

ENV PYTHONUNBUFFERED 1
ENV SIKTEERI_CONFIGURATION dev
ENV DJANGO_HOSTNAME 0.0.0.0:8080
ENV SIKTEERI_ADMIN_EMAIL admin@example.com
ENV SIKTEERI_ADMIN_USERNAME admin
ENV SIKTEERI_ADMIN_PASSWORD salasana

RUN apt-get update && apt-get install -y \
    libldap-dev \
    libsasl2-dev \
    locales \
    && rm -rf /var/lib/apt/lists/*

RUN echo fi_FI.UTF-8 UTF-8 > /etc/locale.gen
RUN locale-gen
ENV LANG fi_FI.UTF-8
ENV LANGUAGE fi_FI:fi
ENV LC_ALL fi_FI.UTF-8
RUN echo "LANG=fi_FI.UTF-8" > /etc/default/locale

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python manage.py migrate
RUN echo "from django.contrib.auth.models import User; User.objects.filter(email='admin@example.com').delete(); User.objects.create_superuser('${SIKTEERI_ADMIN_USERNAME}', '${SIKTEERI_ADMIN_EMAIL}', '${SIKTEERI_ADMIN_PASSWORD}')" | python manage.py shell
RUN python manage.py loaddata membership/fixtures/membership_fees.json
RUN python manage.py generate_test_data

EXPOSE 8080

CMD python manage.py runserver $DJANGO_HOSTNAME