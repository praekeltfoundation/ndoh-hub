FROM praekeltfoundation/django-bootstrap:py3.6

COPY . /app
RUN pip install --no-cache-dir -e . 

ENV DJANGO_SETTINGS_MODULE "ndoh_hub.settings"
RUN ./manage.py collectstatic --noinput
RUN apt-get-install.sh gettext; \
    django-admin compilemessages; \
    apt-get-purge.sh gettext
CMD ["ndoh_hub.wsgi:application"]
