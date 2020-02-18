FROM praekeltfoundation/django-bootstrap:py3.6

COPY setup.py /app
RUN pip install --no-cache-dir -e . 
ENV DJANGO_SETTINGS_MODULE "ndoh_hub.settings"

COPY locale /app
RUN apt-get-install.sh gettext; \
    django-admin compilemessages; \
    apt-get-purge.sh gettext

COPY . /app
RUN ./manage.py collectstatic --noinput
CMD ["ndoh_hub.wsgi:application"]
