"""
Django settings for ndoh_hub project.

For more information on this file, see
https://docs.djangoproject.com/en/1.9/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.9/ref/settings/
"""

from kombu import Exchange, Queue

import os
import dj_database_url
import mimetypes

import django.conf.locale

# Support SVG on admin
mimetypes.add_type("image/svg+xml", ".svg", True)
mimetypes.add_type("image/svg+xml", ".svgz", True)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.9/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'REPLACEME')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', False)

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = (
    # admin
    'django.contrib.admin',
    # core
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # documentation
    'rest_framework_docs',
    # 3rd party
    'channels',
    'raven.contrib.django.raven_compat',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'rest_hooks',
    'simple_history',
    # us
    'registrations',
    'changes'

)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
)

ROOT_URLCONF = 'ndoh_hub.urls'

WSGI_APPLICATION = 'ndoh_hub.wsgi.application'
ASGI_APPLICATION = 'ndoh_hub.routing.application'


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d '
                      '%(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'registrations': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'changes': {
            'handlers': ['console'],
            'level': 'INFO',
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        }
    }
}

# Database
# https://docs.djangoproject.com/en/1.9/ref/settings/#databases

DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get(
            'HUB_DATABASE',
            'postgres://postgres:@localhost/ndoh_hub')),
}


# Internationalization
# https://docs.djangoproject.com/en/1.9/topics/i18n/

LANGUAGE_CODE = 'en-gb'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LANGUAGES = [
    ('afr-za', "Afrikaans"),
    ('eng-za', "English"),
    ('nbl-za', "isiNdebele"),
    ('nso-za', "Sepedi"),
    ('sot-za', "Sesotho"),
    ('ssw-za', "Siswati"),
    ('tsn-za', "Setswana"),
    ('tso-za', "Xitsonga"),
    ('ven-za', "Tshivenda"),
    ('xho-za', "isiXhosa"),
    ('zul-za', "isiZulu"),
]

LANG_INFO = {
    lang[0]: {
        'bidi': False,
        'code': lang[0],
        'name': lang[1],
        'name_local': lang[1],
    } for lang in LANGUAGES
}

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

# Add custom languages not provided by Django
django.conf.locale.LANG_INFO = LANG_INFO

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.9/howto/static-files/

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'django.contrib.staticfiles.finders.FileSystemFinder',
)

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Sentry configuration
RAVEN_CONFIG = {
    # DevOps will supply you with this.
    'dsn': os.environ.get('HUB_SENTRY_DSN', None),
}

# REST Framework conf defaults
REST_FRAMEWORK = {
    'PAGE_SIZE': 1000,
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework.pagination.CursorPagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',)
}

# Webhook event definition
HOOK_EVENTS = {
    # 'any.event.name': 'App.Model.Action' (created/updated/deleted)
    'subscriptionrequest.added': 'registrations.SubscriptionRequest.created+'
}

HOOK_DELIVERER = 'registrations.tasks.deliver_hook_wrapper'

HOOK_AUTH_TOKEN = os.environ.get('HOOK_AUTH_TOKEN', 'REPLACEME')

# Celery configuration options
CELERY_BROKER_URL = os.environ.get('BROKER_URL', 'redis://localhost:6379/0')

CELERY_TASK_DEFAULT_QUEUE = 'ndoh_hub'
CELERY_TASK_QUEUES = (
    Queue('ndoh_hub',
          Exchange('ndoh_hub'),
          routing_key='ndoh_hub'),
)

CELERY_TASK_ALWAYS_EAGER = False

# Tell Celery where to find the tasks
CELERY_IMPORTS = (
    'registrations.tasks',
    'changes.tasks',
)

CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_TASK_ROUTES = {
    'celery.backend_cleanup': {
        'queue': 'mediumpriority',
    },
    'ndoh_hub.registrations.tasks.validate_subscribe': {
        'queue': 'mediumpriority',
    },
    'ndoh_hub.changes.tasks.validate_implement': {
        'queue': 'mediumpriority',
    },
    'registrations.tasks.DeliverHook': {
        'queue': 'priority',
    },
    'ndoh_hub.tasks.fire_metric': {
        'queue': 'metrics',
    },
}

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']

REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

METRICS_REALTIME = [
    'registrations.created.sum',
]
METRICS_SCHEDULED = [  # type: ignore
]
METRICS_SCHEDULED_TASKS = [  # type: ignore
]

METRICS_URL = os.environ.get('METRICS_URL', 'http://metrics/api/v1')
METRICS_AUTH = (
    os.environ.get('METRICS_AUTH_USER', 'REPLACEME'),
    os.environ.get('METRICS_AUTH_PASSWORD', 'REPLACEME'),
)

PREBIRTH_MIN_WEEKS = int(os.environ.get('PREBIRTH_MIN_WEEKS', '4'))

STAGE_BASED_MESSAGING_URL = os.environ.get('STAGE_BASED_MESSAGING_URL',
                                           'http://sbm/api/v1')
STAGE_BASED_MESSAGING_TOKEN = os.environ.get('STAGE_BASED_MESSAGING_TOKEN',
                                             'REPLACEME')
IDENTITY_STORE_URL = os.environ.get('IDENTITY_STORE_URL',
                                    'http://is/api/v1')
IDENTITY_STORE_TOKEN = os.environ.get('IDENTITY_STORE_TOKEN',
                                      'REPLACEME')
MESSAGE_SENDER_URL = os.environ.get('MESSAGE_SENDER_URL',
                                    'http://ms/api/v1')
MESSAGE_SENDER_TOKEN = os.environ.get('MESSAGE_SENDER_TOKEN',
                                      'REPLACEME')
SERVICE_RATING_URL = os.environ.get('SERVICE_RATING_URL',
                                    'http://sr/api/v1')
SERVICE_RATING_TOKEN = os.environ.get('SERVICE_RATING_TOKEN',
                                      'REPLACEME')
JEMBI_BASE_URL = os.environ.get('JEMBI_BASE_URL',
                                'http://jembi/ws/rest/v1/')
JEMBI_USERNAME = os.environ.get('JEMBI_USERNAME', 'test')
JEMBI_PASSWORD = os.environ.get('JEMBI_PASSWORD', 'test')
JUNEBUG_BASE_URL = os.environ.get('JUNEBUG_BASE_URL', 'http://junebug')
JUNEBUG_USERNAME = os.environ.get('JUNEBUG_USERNAME', 'REPLACEME')
JUNEBUG_PASSWORD = os.environ.get('JUNEBUG_PASSWORD', 'REPLACEME')
WHATSAPP_CHANNEL_TYPE = os.environ.get('WHATSAPP_CHANNEL_TYPE', 'wassup')
WASSUP_URL = os.environ.get('WASSUP_URL', 'http://wassup')
WASSUP_TOKEN = os.environ.get('WASSUP_TOKEN', 'wassup-token')
WASSUP_NUMBER = os.environ.get('WASSUP_NUMBER', '+27820000000')

NURSECONNECT_RTHB = os.environ.get(
    'NURSECONNECT_RTHB', 'false').lower() == 'true'

POPI_USSD_CODE = os.environ.get('POPI_USSD_CODE', '*134*550*7#')
OPTOUT_USSD_CODE = os.environ.get('OPTOUT_USSD_CODE', '*134*550*1#')

ENGAGE_HMAC_SECRET = os.environ.get('ENGAGE_HMAC_SECRET', 'REPLACEME')
