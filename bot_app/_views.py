from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings # Pour accéder aux chemins, etc.
import os
import json
import logging

from .tasks import (
    start_trading_bot_task, 
    stop_trading_bot_task, 
    get_bot_status_task,
    get_bot_ohlc_task,
    get_bot_trades_task,
    update_bot_cookies_task
)

logger = logging.getLogger(__name__)
COOKIES_FILE_PATH = os.path.join(settings.BASE_DIR, 'Trading_cookies.json') # Assure-toi que BASE_DIR est bien configuré

class BotControlView(APIView):
    def post(self, request, action):
        logger.info("API Reçue: Action '%s'", action)
        if action == "start":
            # Potentiellement passer une config depuis la requête
            config_override = request.data.get("config", None)
            task = start_trading_bot_task.delay(cookies_path=COOKIES_FILE_PATH, config_override=config_override)
            return Response({"status": "starting", "task_id": task.id, "message": "Bot start task initiated."}, status=status.HTTP_202_ACCEPTED)
        elif action == "stop":
            task = stop_trading_bot_task.delay()
            return Response({"status": "stopping", "task_id": task.id, "message": "Bot stop task initiated."}, status=status.HTTP_202_ACCEPTED)
        else:
            return Response({"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST)

class BotStatusView(APIView):
    def get(self, request):
        logger.debug("API Reçue: Demande de statut")
        # Pour une réponse plus rapide, on pourrait stocker l'état dans Redis via Celery
        # et le lire ici. Pour l'instant, on appelle la tâche (qui peut être lente si elle attend une instance).
        # Alternative: la tâche Celery `get_bot_status_task` pourrait écrire dans un cache.
        # Simplifions pour l'instant en supposant que l'instance est globale dans tasks.py (NON RECOMMANDÉ EN PROD MULTI-WORKER)
        
        # Solution plus robuste: utiliser Celery pour récupérer l'état
        task_result = get_bot_status_task.apply_async()
        try:
            # Attendre le résultat avec un timeout pour ne pas bloquer l'API trop longtemps
            bot_status_data = task_result.get(timeout=5) 
            return Response(bot_status_data, status=status.HTTP_200_OK)
        except Exception as e: # TimeoutError, etc.
            logger.warning("Timeout ou erreur lors de la récupération du statut du bot via Celery: %s", e)
            return Response({"status": "unknown", "is_running": False, "message": "Could not retrieve bot status in time."}, status=status.HTTP_504_GATEWAY_TIMEOUT)


class BotCookiesView(APIView):
    def get(self, request):
        logger.debug("API Reçue: Demande des cookies actuels")
        try:
            with open(COOKIES_FILE_PATH, "r") as f:
                cookies_data = json.load(f)
            return Response(cookies_data, status=status.HTTP_200_OK)
        except FileNotFoundError:
            return Response({"error": "Cookies file not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("Erreur API lecture cookies: %s", e)
            return Response({"error": "Could not read cookies file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def post(self, request):
        logger.info("API Reçue: Mise à jour des cookies")
        new_cookies = request.data.get("cookies")
        if not isinstance(new_cookies, list):
            return Response({"error": "Invalid cookies format. Expected a list."}, status=status.HTTP_400_BAD_REQUEST)
        
        task = update_bot_cookies_task.delay(cookies_json_list=new_cookies, cookies_path=COOKIES_FILE_PATH)
        return Response({"status": "cookies_update_initiated", "task_id": task.id, "message": "Cookies update task sent. Bot restart will be needed."}, status=status.HTTP_202_ACCEPTED)

class BotLogsView(APIView): # Très basique, pour des logs plus avancés, utiliser un système de logging centralisé
    def get(self, request):
        logger.debug("API Reçue: Demande de logs")
        log_file_path = getattr(settings, 'LOGGING_FILE_PATH', None) # Tu devras définir ça dans settings.py
        if not log_file_path or not os.path.exists(log_file_path):
             return Response({"error": "Log file path not configured or file not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            lines_to_fetch = int(request.query_params.get("lines", 100))
            with open(log_file_path, 'r') as f:
                # Technique simple pour les dernières lignes, peut être inefficace pour gros fichiers
                lines = f.readlines()
                last_lines = lines[-lines_to_fetch:]
            return Response({"logs": "".join(last_lines)}, status=status.HTTP_200_OK) # Renvoie une chaîne, mieux serait une liste de lignes
        except Exception as e:
            logger.error("Erreur API lecture logs: %s", e)
            return Response({"error": "Could not read log file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class BotOHLCView(APIView):
    def get(self, request):
        last_n = int(request.query_params.get("last_n", 20))
        task_result = get_bot_ohlc_task.apply_async(args=[last_n])
        try:
            ohlc_data = task_result.get(timeout=3)
            return Response(ohlc_data, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Could not retrieve OHLC data."}, status=status.HTTP_504_GATEWAY_TIMEOUT)

class BotTradesHistoryView(APIView):
    def get(self, request):
        last_n = int(request.query_params.get("last_n", 20))
        task_result = get_bot_trades_task.apply_async(args=[last_n])
        try:
            trades_data = task_result.get(timeout=3)
            return Response(trades_data, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Could not retrieve trade history."}, status=status.HTTP_504_GATEWAY_TIMEOUT)

# Tu peux ajouter un endpoint pour la config plus tard