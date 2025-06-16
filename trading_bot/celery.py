import os
from celery import Celery

# Définir le module de settings Django par défaut pour le programme 'celery'.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trading_bot.settings')

app = Celery('trading_bot')

# Utiliser une chaîne ici signifie que le worker n'a pas besoin de sérialiser
# l'objet de configuration pour les process enfants.
# - namespace='CELERY' signifie que toutes les clés de config Celery
#   doivent avoir un préfixe `CELERY_`.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Charger les modules de tâches de toutes les apps Django enregistrées.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')