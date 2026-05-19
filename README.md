# Django Settings
SECRET_KEY=your-secret-key-change-this-in-production
DEBUG=True
ENV=dev

# Database - Development
DB_NAME=campusconnect_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432

# Database - Production
PROD_DB_NAME=campusconnect_prod_db
PROD_DB_USER=postgres
PROD_DB_PASSWORD=prod_password
PROD_DB_HOST=localhost
PROD_DB_PORT=5432

# Database - Staging
STAGING_DB_NAME=campusconnect_staging_db
STAGING_DB_USER=postgres
STAGING_DB_PASSWORD=staging_password
STAGING_DB_HOST=localhost
STAGING_DB_PORT=5432

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USER=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_FROM=noreply@campusconnect.com

# Redis Configuration
REDIS_URL=redis://127.0.0.1:6379/1

# Cache Configuration
CACHE_TTL=86400

# Celery Configuration
CELERY_BROKER_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0


SWAGGER_PROTECT_USERNAME=admin@admin.com
SWAGGER_PROTECT_PASSWORD=admin