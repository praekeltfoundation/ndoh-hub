from ndoh_hub.settings import *  # noqa: F403 # flake8: noqa

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "TESTSEKRET"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

CELERY_TASK_EAGER_PROPAGATES = False  # To test error handling
CELERY_TASK_ALWAYS_EAGER = True

PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

REST_FRAMEWORK["PAGE_SIZE"] = 2  # noqa: F405

WHATSAPP_NAMESPACE = "test-namespace"

HCS_STUDY_A_ACTIVE = True
HCS_STUDY_B_ACTIVE = True
HCS_STUDY_C_ACTIVE = True

HANDLE_EXPIRED_HELPDESK_CONTACTS_ENABLED = True

MQR_CONTENTREPO_URL = "http://contentrepo"
MQR_SEND_AIRTIME_FLOW_ID = "mqr-send-airtime-flow-uuid"

AAQ_CORE_API_URL = "http://aaqcore"
AAQ_UD_API_URL = "http://aaqud"
AAQ_V2_API_URL = "http://aaq_v2"


ADA_EDC_STUDY_URL = "http://castor"
ADA_EDC_STUDY_ID = "test-study-id"
ADA_EDC_INSTITUTE_ID = "test-institute-id"
