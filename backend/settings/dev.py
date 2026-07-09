from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]

if os.environ.get("DATABASE_TYPE") == "sqlite3":

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

else:

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME"),
            "USER": os.environ.get("DB_USER"),
            "PASSWORD": os.environ.get("DB_PASSWORD"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND")
EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_FROM = os.environ.get("EMAIL_FROM")


CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = True

CORS_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5501",
    "http://127.0.0.1:5500",
    "http://192.168.0.199:5501",
    "http://192.168.1.179:5500",
    "http://192.168.0.198:5501",
    "http://172.26.80.1:5500",
    "http://192.168.1.127:5500",
    "http://127.0.0.1:5500",
]

BASE_FRONTEND_URL = os.environ.get("BASE_FRONTEND_URL")

# Payment Gateway Keys
PAYSTACK_SECRET_KEY=os.getenv('PAYSTACK_SECRET_KEY')
PAYSTACK_INITIALIZE_URL=os.getenv('PAYSTACK_INITIALIZE_URL')
PAYSTACK_VERIFY_URL=os.getenv('PAYSTACK_VERIFY_URL')

# Flutterwave Gateway Keys
FLUTTERWAVE_SECRET_KEY=os.getenv('FLUTTERWAVE_SECRET_KEY')
FLUTTERWAVE_INITIALIZE_URL=os.getenv('FLUTTERWAVE_INITIALIZE_URL')
FLUTTERWAVE_VERIFY_URL=os.getenv('FLUTTERWAVE_VERIFY_URL')
