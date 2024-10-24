"""
Django settings for ndoh_hub project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

import mimetypes
import os

import dj_database_url
import django.conf.locale
import environ
from celery.schedules import crontab
from kombu import Exchange, Queue

env = environ.Env(ENABLE_UNSENT_EVENT_ACTION=(bool, True))

# Support SVG on admin
mimetypes.add_type("image/svg+xml", ".svg", True)
mimetypes.add_type("image/svg+xml", ".svgz", True)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "template")
# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get("SECRET_KEY", "REPLACEME")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get("DEBUG", False)

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = (
    # admin
    "django.contrib.admin",
    # core
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # 3rd party
    "raven.contrib.django.raven_compat",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "simple_history",
    "django_prometheus",
    # us
    "registrations",
    "changes",
    "eventstore",
    "aaq",
)


MIDDLEWARE = (
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
)

ROOT_URLCONF = "ndoh_hub.urls"

WSGI_APPLICATION = "ndoh_hub.wsgi.application"
ASGI_APPLICATION = "ndoh_hub.routing.application"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d "
            "%(thread)d %(message)s"
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "null": {"class": "logging.NullHandler"},
    },
    "loggers": {
        "registrations": {"handlers": ["console"], "level": "INFO"},
        "changes": {"handlers": ["console"], "level": "INFO"},
        "eventstore": {"handlers": ["console"], "level": "INFO"},
        "django.request": {"handlers": ["console"], "level": "ERROR"},
        "django.db.backends": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    "default": dj_database_url.config(
        default=os.environ.get(
            "HUB_DATABASE", "postgres://postgres@localhost/ndoh_hub"
        ),
        engine="django_prometheus.db.backends.postgresql",
    )
}

PROMETHEUS_EXPORT_MIGRATIONS = False


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

LANGUAGES = [
    ("afr-za", "Afrikaans"),
    ("eng-za", "English"),
    ("nbl-za", "isiNdebele"),
    ("nso-za", "Sepedi"),
    ("sot-za", "Sesotho"),
    ("ssw-za", "Siswati"),
    ("tsn-za", "Setswana"),
    ("tso-za", "Xitsonga"),
    ("ven-za", "Tshivenda"),
    ("xho-za", "isiXhosa"),
    ("zul-za", "isiZulu"),
    ("en", "English"),
]

LANG_INFO = {
    lang[0]: {"bidi": False, "code": lang[0], "name": lang[1], "name_local": lang[1]}
    for lang in LANGUAGES
}

LOCALE_PATHS = [os.path.join(BASE_DIR, "locale")]

# Add custom languages not provided by Django
django.conf.locale.LANG_INFO = LANG_INFO

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "django.contrib.staticfiles.finders.FileSystemFinder",
)

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATIC_URL = "/static/"

STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [TEMPLATES_DIR],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

# Sentry configuration
RAVEN_CONFIG = {
    # DevOps will supply you with this.
    "dsn": os.environ.get("HUB_SENTRY_DSN", None)
}

# REST Framework conf defaults
REST_FRAMEWORK = {
    "PAGE_SIZE": 1000,
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.CursorPagination",
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework.authentication.BasicAuthentication",
        "ndoh_hub.auth.CachedTokenAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_FILTER_BACKENDS": ("django_filters.rest_framework.DjangoFilterBackend",),
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.ScopedRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {
        "covid19triage.create": os.environ.get(
            "COVID19_TRIAGE_CREATE_THROTTLE_RATE", "30/second"
        ),
        "covid19triage.list": os.environ.get(
            "COVID19_TRIAGE_LIST_THROTTLE_RATE", "60/minute"
        ),
    },
}

# Celery configuration options
CELERY_BROKER_URL = os.environ.get("BROKER_URL", "redis://localhost:6379/0")

CELERY_TASK_DEFAULT_QUEUE = "ndoh_hub"
CELERY_TASK_QUEUES = (Queue("ndoh_hub", Exchange("ndoh_hub"), routing_key="ndoh_hub"),)

CELERY_TASK_ALWAYS_EAGER = False

# Tell Celery where to find the tasks
CELERY_IMPORTS = ("eventstore.tasks",)

CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_TASK_ROUTES = {
    "celery.backend_cleanup": {"queue": "mediumpriority"},
    "ndoh_hub.changes.tasks.validate_implement": {"queue": "mediumpriority"},
}

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

HANDLE_EXPIRED_HELPDESK_CONTACTS_ENABLED = env.bool(
    "HANDLE_EXPIRED_HELPDESK_CONTACTS_ENABLED", False
)
HANDLE_EXPIRED_HELPDESK_CONTACTS_HOUR = env.str(
    "HANDLE_EXPIRED_HELPDESK_CONTACTS_HOUR", "3"
)

RANDOM_CONTACTS_HOUR = env.str("RANDOM_CONTACTS_HOUR", "2")
RANDOM_CONTACTS_DAY_OF_WEEK = env.str("RANDOM_CONTACTS_DAY_OF_WEEK", "4")

CELERY_BEAT_SCHEDULE = {
    "handle-expired-helpdesk-contacts": {
        "task": "eventstore.tasks.handle_expired_helpdesk_contacts",
        "schedule": crontab(minute="0", hour=HANDLE_EXPIRED_HELPDESK_CONTACTS_HOUR),
    },
    "post-random-mc-contacts-to-slack-channel": {
        "task": "eventstore.tasks.post_random_mc_contacts_to_slack_channel",
        "schedule": crontab(
            minute="0",
            hour=RANDOM_CONTACTS_HOUR,
            day_of_week=RANDOM_CONTACTS_DAY_OF_WEEK,
        ),
    },
    "process-whatsapp-template-send-status": {
        "task": "eventstore.tasks.process_whatsapp_template_send_status",
        "schedule": 300.0,
    },
}

BULK_INSERT_EVENTS_ENABLED = env.bool("BULK_INSERT_EVENTS_ENABLED", False)
BULK_INSERT_EVENTS_FLUSH_EVERY = env.int("BULK_INSERT_EVENTS_FLUSH_EVERY", 100)
BULK_INSERT_EVENTS_FLUSH_INTERVAL = env.int("BULK_INSERT_EVENTS_FLUSH_INTERVAL", 10)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

METRICS_REALTIME = []  # type: ignore
METRICS_SCHEDULED = []  # type: ignore
METRICS_SCHEDULED_TASKS = []  # type: ignore

PREBIRTH_MIN_WEEKS = int(os.environ.get("PREBIRTH_MIN_WEEKS", "4"))
WHATSAPP_EXPIRY_SMS_BOUNCE_DAYS = int(
    os.environ.get("WHATSAPP_EXPIRY_SMS_BOUNCE_DAYS", "30")
)

STAGE_BASED_MESSAGING_URL = os.environ.get(
    "STAGE_BASED_MESSAGING_URL", "http://sbm/api/v1"
)
STAGE_BASED_MESSAGING_TOKEN = os.environ.get("STAGE_BASED_MESSAGING_TOKEN", "REPLACEME")
IDENTITY_STORE_URL = os.environ.get("IDENTITY_STORE_URL", "http://is/api/v1")
IDENTITY_STORE_TOKEN = os.environ.get("IDENTITY_STORE_TOKEN", "REPLACEME")
MESSAGE_SENDER_URL = os.environ.get("MESSAGE_SENDER_URL", "http://ms/api/v1")
MESSAGE_SENDER_TOKEN = os.environ.get("MESSAGE_SENDER_TOKEN", "REPLACEME")
SERVICE_RATING_URL = os.environ.get("SERVICE_RATING_URL", "http://sr/api/v1")
SERVICE_RATING_TOKEN = os.environ.get("SERVICE_RATING_TOKEN", "REPLACEME")
JEMBI_BASE_URL = os.environ.get("JEMBI_BASE_URL", "http://jembi/ws/rest/v1/")
JEMBI_USERNAME = os.environ.get("JEMBI_USERNAME", "test")
JEMBI_PASSWORD = os.environ.get("JEMBI_PASSWORD", "test")
JUNEBUG_BASE_URL = os.environ.get("JUNEBUG_BASE_URL", "http://junebug")
JUNEBUG_USERNAME = os.environ.get("JUNEBUG_USERNAME", "REPLACEME")
JUNEBUG_PASSWORD = os.environ.get("JUNEBUG_PASSWORD", "REPLACEME")
WHATSAPP_CHANNEL_TYPE = os.environ.get("WHATSAPP_CHANNEL_TYPE", "wassup")
ENGAGE_URL = os.environ.get("WASSUP_URL", "http://engage")
ENGAGE_TOKEN = os.environ.get("WASSUP_TOKEN", "engage-token")
TURN_URL = os.environ.get("TURN_URL", "http://turn")
TURN_TOKEN = os.environ.get("TURN_TOKEN", "turn-token")
WHATSAPP_NAMESPACE = os.environ.get(
    "WHATSAPP_NAMESPACE", "ff7348dc_a184_4ec1_bf0a_47dc38679d42"
)

NURSECONNECT_RTHB = os.environ.get("NURSECONNECT_RTHB", "false").lower() == "true"

POPI_USSD_CODE = os.environ.get("POPI_USSD_CODE", "*134*550*7#")
OPTOUT_USSD_CODE = os.environ.get("OPTOUT_USSD_CODE", "*134*550*1#")

ENGAGE_HMAC_SECRET = os.environ.get("ENGAGE_HMAC_SECRET", "REPLACEME")
ENGAGE_CONTEXT_HMAC_SECRET = os.environ.get("ENGAGE_CONTEXT_HMAC_SECRET", "REPLACEME")
TURN_HMAC_SECRET = os.environ.get("TURN_HMAC_SECRET", "REPLACEME")

ENABLE_UNSENT_EVENT_ACTION = env("ENABLE_UNSENT_EVENT_ACTION")
ENABLE_JEMBI_EVENTS = env.bool("ENABLE_JEMBI_EVENTS", True)

CACHES = {
    "default": env.cache(default="locmemcache://"),
    "locmem": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
    "redis": env.cache(
        "REDIS_URL", default=REDIS_URL, backend="django_redis.cache.RedisCache"
    ),
}

EXTERNAL_REGISTRATIONS_V2 = env.bool("EXTERNAL_REGISTRATIONS_V2", False)

if EXTERNAL_REGISTRATIONS_V2:
    RAPIDPRO_URL = env.str("RAPIDPRO_URL")
    RAPIDPRO_TOKEN = env.str("RAPIDPRO_TOKEN")
    RAPIDPRO_PUBLIC_REGISTRATION_FLOW = env.str("RAPIDPRO_PUBLIC_REGISTRATION_FLOW")
    RAPIDPRO_CHW_REGISTRATION_FLOW = env.str("RAPIDPRO_CHW_REGISTRATION_FLOW")
    RAPIDPRO_CLINIC_REGISTRATION_FLOW = env.str("RAPIDPRO_CLINIC_REGISTRATION_FLOW")
    RAPIDPRO_JEMBI_REGISTRATION_FLOW = env.str("RAPIDPRO_JEMBI_REGISTRATION_FLOW")

DISABLE_WHATSAPP_EVENT_ACTIONS = env.bool("DISABLE_WHATSAPP_EVENT_ACTIONS", False)

ENABLE_EVENTSTORE_WHATSAPP_ACTIONS = env.bool(
    "ENABLE_EVENTSTORE_WHATSAPP_ACTIONS", False
)
if ENABLE_EVENTSTORE_WHATSAPP_ACTIONS:
    RAPIDPRO_OPERATOR_REPLY_FLOW = env.str("RAPIDPRO_OPERATOR_REPLY_FLOW")
    RAPIDPRO_UNSENT_EVENT_FLOW = env.str("RAPIDPRO_UNSENT_EVENT_FLOW")
    RAPIDPRO_OPTOUT_FLOW = env.str("RAPIDPRO_OPTOUT_FLOW")
    RAPIDPRO_EDD_LABEL_FLOW = env.str("RAPIDPRO_EDD_LABEL_FLOW")

DISABLE_EDD_LABEL_FLOW = env.bool("DISABLE_EDD_LABEL_FLOW", False)

RAPIDPRO_PREBIRTH_CLINIC_FLOW = env.str("RAPIDPRO_PREBIRTH_CLINIC_FLOW", None)
RAPIDPRO_POSTBIRTH_CLINIC_FLOW = env.str("RAPIDPRO_POSTBIRTH_CLINIC_FLOW", None)

DISABLE_SMS_FAILURE_OPTOUTS = env.bool("DISABLE_SMS_FAILURE_OPTOUTS", False)

HELPDESK_TIMEOUT_DAYS = env.int("HELPDESK_TIMEOUT_DAYS", 10)

FORGET_OPTOUT_TASK_COUNTDOWN = env.int("FORGET_OPTOUT_TASK_COUNTDOWN", 600)

# HealthCheck
HC_TURN_URL = env.str("HC_TURN_URL", None)
HC_TURN_TOKEN = env.str("HC_TURN_TOKEN", None)
HC_RAPIDPRO_URL = env.str("HC_RAPIDPRO_URL", None)
HC_RAPIDPRO_TOKEN = env.str("HC_RAPIDPRO_TOKEN", None)

HCS_STUDY_A_ACTIVE = env.bool("HCS_STUDY_A_ACTIVE", False)
HCS_STUDY_A_WHITELIST = env.list("HCS_STUDY_A_WHITELIST", default=["*"])
HCS_STUDY_A_CREATED_BY = env.str("HCS_STUDY_A_CREATED_BY", "whatsapp_healthcheck")
HCS_STUDY_B_ACTIVE = env.bool("HCS_STUDY_B_ACTIVE", True)
HCS_STUDY_B_WHITELIST = env.list("HCS_STUDY_B_WHITELIST", default=["*"])
HCS_STUDY_B_CREATED_BY = env.list(
    "HCS_STUDY_B_CREATED_BY",
    default=["whatsapp_higherhealth_healthcheck", "ussd_higherhealth_healthcheck"],
)
HCS_STUDY_C_ACTIVE = env.bool("HCS_STUDY_C_ACTIVE", False)
HCS_STUDY_C_REGISTRATION_FLOW_ID = env.str("HCS_STUDY_C_REGISTRATION_FLOW_ID", None)


RAPIDPRO_URL = env.str("RAPIDPRO_URL", None)
RAPIDPRO_TOKEN = env.str("RAPIDPRO_TOKEN", None)
SLACK_URL = env.str("SLACK_URL", None)
SLACK_TOKEN = env.str("SLACK_TOKEN", None)
SLACK_CHANNEL = env.str("SLACK_CHANNEL", None)
RANDOM_CONTACT_LIMIT = env.str("RANDOM_CONTACT_LIMIT", 10)

# AAQ-Beta
AAQ_CORE_API_URL = env.str("AAQ_CORE_API_URL", None)
AAQ_CORE_INBOUND_CHECK_AUTH = env.str("AAQ_CORE_INBOUND_CHECK_AUTH", None)
AAQ_UD_API_URL = env.str("AAQ_UD_API_URL", None)
AAQ_UD_INBOUND_CHECK_AUTH = env.str("AAQ_UD_INBOUND_CHECK_AUTH", None)

# AAQ V2
AAQ_V2_API_URL = env.str("AAQ_V2_API_URL", None)
AAQ_V2_AUTH = env.str("AAQ_V2_AUTH", None)

ALERT_OPTOUT_PHRASE = env.str("ALERT_OPTOUT_PHRASE", "Opt out of alerts")

WHATSAPP_TEMPLATE_SEND_TIMEOUT_HOURS = env.int(
    "WHATSAPP_TEMPLATE_SEND_TIMEOUT_HOURS", 3
)
