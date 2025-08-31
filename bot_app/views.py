from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .utils import convert_cookies 
from django.conf import settings
import os
import json
import logging
from typing import List, Literal
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .tasks import (
    start_trading_bot_task,
    stop_trading_bot_task,
    get_bot_status_task,
    get_bot_ohlc_task,
    get_bot_trades_task,
    update_bot_cookies_task,
    debug_hello_task
)

logger = logging.getLogger(__name__)
COOKIES_FILE_PATH = os.path.join(settings.BASE_DIR, 'Trading_cookies.json')

class BotViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"], url_path="debug")
    def debug(self, request):
        logger.warning("API Reçue: Démarrage de la tâche de débogage")
        message = "Dieu-Donnee is testing me!"
        task = debug_hello_task.delay(message=message)
        return Response({"status": "debug_task_initiated", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["post"], url_path="start")
    def start(self, request):
        logger.warning("API Reçue: Démarrage du bot de trading")
        config_override = request.data.get("config")
        task = start_trading_bot_task.delay(cookies_path=COOKIES_FILE_PATH, config_override=config_override)
        
        return Response({"status": "starting", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["post"], url_path="stop")
    def stop(self, request):
        logger.warning("API Reçue: Arrêt du bot de trading")
        task = stop_trading_bot_task.delay()
        return Response({"status": "stopping", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"], url_path="status")
    def status(self, request):
        logger.debug("API Reçue: Demande de statut du bot de trading")
        task_result = get_bot_status_task.apply_async()
        try:
            bot_status_data = task_result.get(timeout=5)
            return Response(bot_status_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.warning("Erreur récupération statut bot : %s", e)
            return Response({"status": "unknown", "is_running": False}, status=status.HTTP_504_GATEWAY_TIMEOUT)


    @swagger_auto_schema(
        method='get',
        operation_description="Récupère les commandes de l'utilisateur, avec possibilité de filtrer par statut.",
        manual_parameters=[
            openapi.Parameter(
                'cookies',
                openapi.IN_QUERY,
                description="Liste des cookies à utiliser pour la commande",
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_STRING),
                required=False
            ),
        ]
    )
    @action(detail=False, methods=["get", "post"], url_path="cookies")
    def cookies(self, request):
        logger.debug("API Reçue: Demande de cookies ou mise à jour des cookies")
        if request.method == "GET":
            try:
                with open(COOKIES_FILE_PATH, "r") as f:
                    cookies_data = json.load(f)
                return Response(cookies_data, status=status.HTTP_200_OK)
            except FileNotFoundError:
                return Response({"error": "Cookies file not found."}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                logger.error("Erreur lecture cookies : %s", e)
                return Response({"error": "Could not read cookies file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        elif request.method == "POST":
            new_cookies = request.query_params.get('cookies')
            editor_cookies=json.loads(new_cookies) if isinstance(new_cookies, str) else new_cookies
            selenium_ready=convert_cookies(editor_cookies,source="editor")
            if not isinstance(selenium_ready, list):
                return Response({"error": "Expected a list of cookies."}, status=status.HTTP_400_BAD_REQUEST)

            task = update_bot_cookies_task.delay(cookies_json_list=editor_cookies, cookies_path=COOKIES_FILE_PATH)
            return Response({"status": "cookies_update_initiated", "task_id": task.id}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["get"], url_path="logs")
    def logs(self, request):
        logger.debug("API Reçue: Demande de logs du bot de trading")
        log_file_path = getattr(settings, 'LOGGING_FILE_PATH', None)
        if not log_file_path or not os.path.exists(log_file_path):
            return Response({"error": "Log file not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            lines_to_fetch = int(request.query_params.get("lines", 100))
            with open(log_file_path, 'r') as f:
                lines = f.readlines()
                last_lines = lines[-lines_to_fetch:]
            return Response({"logs": "".join(last_lines)}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Erreur lecture logs : %s", e)
            return Response({"error": "Could not read log file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

    @action(detail=False, methods=["post"], url_path="clear")
    def clear(self, request):
        logger.warning("API Reçue: Effacement des données du bot de trading")
        log_file_path = getattr(settings, 'LOGGING_FILE_PATH', None)
        if log_file_path and os.path.exists(log_file_path):
            try:
                with open(log_file_path, 'w') as f:
                    f.write("")  # Vide le fichier de log
                logger.info("Logs cleared successfully.")
            except Exception as e:
                logger.error("Error clearing logs: %s", e)
                return Response({"error": "Could not clear log file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({"status": "cleared", "message": "Bot data cleared."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="ohlc")
    def ohlc(self, request):
        logger.debug("API Reçue: Demande de données OHLC du bot de trading")
        last_n = int(request.query_params.get("last_n", 20))
        task_result = get_bot_ohlc_task.apply_async(args=[last_n])
        try:
            ohlc_data = task_result.get(timeout=3)
            return Response(ohlc_data, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Could not retrieve OHLC data."}, status=status.HTTP_504_GATEWAY_TIMEOUT)

    @action(detail=False, methods=["get"], url_path="trades")
    def trades(self, request):
        logger.debug("API Reçue: Demande de l'historique des trades du bot de trading")
        last_n = int(request.query_params.get("last_n", 20))
        task_result = get_bot_trades_task.apply_async(args=[last_n])
        try:
            trades_data = task_result.get(timeout=3)
            return Response(trades_data, status=status.HTTP_200_OK)
        except Exception:
            return Response({"error": "Could not retrieve trade history."}, status=status.HTTP_504_GATEWAY_TIMEOUT)
