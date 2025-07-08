FROM ghcr.io/praekeltfoundation/docker-django-bootstrap-nw:py3.10-bullseye

ENV DJANGO_SETTINGS_MODULE "ndoh_hub.settings"

COPY . /app

RUN pip install -e .
    
RUN apt-get-install.sh gettext; \
    django-admin compilemessages; \
    apt-get-purge.sh gettext

RUN ./manage.py collectstatic --noinput
CMD [\
    "ndoh_hub.wsgi:application",\
    "--workers=2",\
    "--threads=4",\
    "--worker-class=gthread",\
    "--worker-tmp-dir=/dev/shm"\
]
