import os
import django
from django.apps import apps
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import transaction

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trading_bot.settings')
django.setup()

call_command('makemigrations', '--noinput')
call_command('migrate', '--noinput')
call_command('collectstatic', '--noinput')

User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser(
        first_name="Admin",
        last_name="Trading Bot",
        email='admin@example.com',
        password='password123'
    )
    print("Superuser creation successful.")
else:
    print("Superuser already exists.")