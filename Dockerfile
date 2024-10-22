FROM ghcr.io/praekeltfoundation/docker-django-bootstrap-nw:py3.9-bullseye

RUN pip install poetry==1.8.3
ENV DJANGO_SETTINGS_MODULE "ndoh_hub.settings"

COPY . /app
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi --no-cache
    
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
