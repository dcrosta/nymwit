from os.path import abspath, dirname, join

# Django settings for nymwit project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

USE_I18N = False
USE_L10N = False

SECRET_KEY = '12345678901234567890'

TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.filesystem.Loader',
)

TEMPLATE_DIRS = (
    # the base template is located here
    abspath(join(dirname(__file__), 'templates')),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.static',
    'django.contrib.messages.context_processors.messages'
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

ROOT_URLCONF = 'nymwit.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'nymwit.game',
    'nymwit.account',
)

# See http://docs.djangoproject.com/en/dev/topics/logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)-8s  %(asctime)s  %(name)s  [file:%(filename)s:%(lineno)s][pid:%(process)d]  %(message)s'
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'jobs': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        }
    }
}

MANAGERS = ADMINS = (
    ('Dan Crosta', 'dcrosta@late.am'),
)

STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'
LOGIN_REDIRECT_URL = '/'
LOGIN_URL = '/account/login/'

AUTHENTICATION_BACKENDS = (
    'mongoengine.django.auth.MongoEngineBackend',
)

SESSION_ENGINE = 'mongoengine.django.sessions'

APPEND_SLASH = True

try:
    from local_settings import *
except:
    from json import load
    from mongoengine import connect
    config = load(file('/home/dotcloud/environment.json'))

    # "DOTCLOUD_ENVIRONMENT": "default",
    # "DOTCLOUD_MONGO_MONGODB_PORT": "10372",
    # "DOTCLOUD_PROJECT": "nymwit",
    # "DOTCLOUD_SERVICE_NAME": "www",
    # "DOTCLOUD_MONGO_MONGODB_PASSWORD": "",
    # "DOTCLOUD_MONGO_MONGODB_LOGIN": "root",
    # "DOTCLOUD_SERVICE_ID": "0",
    # "DOTCLOUD_MONGO_MONGODB_HOST": "a792622a.dotcloud.com",
    # "DOTCLOUD_MONGO_MONGODB_URL": "mongodb://..."

    connect(
        'nymwit',
        host=config['DOTCLOUD_MONGO_MONGODB_HOST'],
        port=int(config['DOTCLOUD_MONGO_MONGODB_PORT']),
        username=config['DOTCLOUD_MONGO_MONGODB_LOGIN'],
        password=config['DOTCLOUD_MONGO_MONGODB_PASSWORD'],
        tz_aware=True,
    )

