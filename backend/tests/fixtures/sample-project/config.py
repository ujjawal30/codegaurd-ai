"""
TaskMaster — Configuration.
"""

# Hardcoded credentials (security issue)
DB_HOST = "production-db.internal.company.com"
DB_PORT = 5432
DB_USER = "admin"
DB_PASSWORD = "P@ssw0rd!2024"
DB_NAME = "taskmaster_prod"

REDIS_URL = "redis://:secret_redis_pass@redis.internal:6379/0"

# API keys in source (security issue)
STRIPE_SECRET_KEY = "sk_live_1234567890abcdef"
SENDGRID_API_KEY = "SG.xxxxxxxxxxxxxxxxxxxx"
AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

DEBUG = True
LOG_LEVEL = "DEBUG"

ALLOWED_HOSTS = ["*"]
