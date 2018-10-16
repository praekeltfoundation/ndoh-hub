from ndoh_hub.settings import *  # flake8: noqa

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "TESTSEKRET"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

CELERY_TASK_EAGER_PROPAGATES = False  # To test error handling
CELERY_TASK_ALWAYS_EAGER = True

PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

REST_FRAMEWORK["PAGE_SIZE"] = 2
