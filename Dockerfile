FROM praekeltfoundation/django-bootstrap:py3

COPY . /app
COPY entrypoint.sh /scripts/django-entrypoint.sh
COPY nginx.conf /etc/nginx/conf.d/django.conf
RUN pip install -e .

ENV DJANGO_SETTINGS_MODULE "ndoh_hub.settings"
RUN ./manage.py collectstatic --noinput
CMD ["ndoh_hub.wsgi:application"]
