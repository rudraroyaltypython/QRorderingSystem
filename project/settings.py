from pathlib import Path
import os
import socket

# ---------------------------
# BASE CONFIG
# ---------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-change-this-for-prod'
DEBUG = True
ALLOWED_HOSTS = ["*", "127.0.0.1", "localhost"]

# ✅ Detect local IP for LAN usage
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google DNS
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

SERVER_IP = get_local_ip()
ALLOWED_HOSTS.append(SERVER_IP)

# ---------------------------
# APPS
# ---------------------------
INSTALLED_APPS = [
    'admin_interface',
    'colorfield',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'orders',
    'config',
]

# ---------------------------
# MIDDLEWARE
# ---------------------------
MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'orders.middleware.LicenseCheckMiddleware',  # custom license check
]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# ---------------------------
# URLS & TEMPLATES
# ---------------------------
ROOT_URLCONF = 'project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.template.context_processors.static',  # ✅ added
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'config.context_processors.site_config',
            ],
        },
    },
]

WSGI_APPLICATION = 'project.wsgi.application'

# ---------------------------
# DATABASE (SQLite for local dev)
# ---------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'qrorder_db',  # Change to your local DB name
        'USER': 'root',  # Or your local MySQL username
        'PASSWORD': 'root@123',  # Your MySQL password
        'HOST': '127.0.0.1',  # localhost
        'PORT': '3306',  # MySQL default port
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        },
    }
}

# ---------------------------
# AUTH & LOCALIZATION
# ---------------------------
AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # ✅ Indian time
USE_I18N = True
USE_L10N = True
USE_TZ = True

# ---------------------------
# STATIC & MEDIA
# ---------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]  # make sure folder exists
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------
# SECURITY
# ---------------------------
X_FRAME_OPTIONS = "SAMEORIGIN"
SILENCED_SYSTEM_CHECKS = ["security.W019"]

# ---------------------------
# DRF CONFIG
# ---------------------------
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny'
    ]
}
