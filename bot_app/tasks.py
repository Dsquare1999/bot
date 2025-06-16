from celery import shared_task
from bot_app.services.trading_logic import TradingBot # Assure-toi que le chemin est correct
import logging

logger = logging.getLogger(__name__)

# Variable globale pour garder une instance du bot (simpliste, pour un seul worker)
# Pour plusieurs workers, il faudrait une gestion d'état plus complexe (Redis, DB)
# ou s'assurer qu'un seul worker exécute une instance de bot donnée à la fois.
current_bot_instance = None 

@shared_task(bind=True, name='bot_app.tasks.start_trading_bot_task')
def start_trading_bot_task(self, cookies_path="Trading_cookies.json", config_override=None):
    global current_bot_instance
    logger.info("🤖 Tâche Celery 'start_trading_bot_task' initiée.")
    
    if current_bot_instance and current_bot_instance.is_running:
        logger.warning("🚦 Une instance du bot semble déjà tourner. Annulation du démarrage.")
        return {"status": "already_running", "message": "Bot is already running."}

    try:
        # Charger la config depuis Django settings ou un fichier de config
        # Pour l'instant, on utilise config_override ou les défauts de la classe.
        bot_config = config_override if config_override else None 
        
        current_bot_instance = TradingBot(cookies_path=cookies_path, config=bot_config)
        current_bot_instance.start() # Ceci est bloquant, donc la tâche Celery va tourner tant que le bot tourne.
        
        # Si .start() se termine (par exemple, si is_running devient False), la tâche se termine aussi.
        logger.info("🏁 Tâche Celery 'start_trading_bot_task' terminée (le bot s'est arrêté).")
        return {"status": "stopped", "message": "Bot process finished."}
    except Exception as e:
        logger.critical("💥 Erreur critique dans la tâche Celery: %s", e, exc_info=True)
        if current_bot_instance: # Tenter un arrêt propre
            current_bot_instance.stop()
        current_bot_instance = None
        # Tu peux relancer la tâche ou notifier une erreur ici.
        # self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': str(e)})
        raise # Permet à Celery de marquer la tâche comme échouée.

@shared_task(name='bot_app.tasks.stop_trading_bot_task')
def stop_trading_bot_task():
    global current_bot_instance
    logger.info("🛑 Tâche Celery 'stop_trading_bot_task' initiée.")
    if current_bot_instance and current_bot_instance.is_running:
        current_bot_instance.stop()
        current_bot_instance = None # Libérer l'instance
        logger.info("✅ Bot arrêté via la tâche Celery.")
        return {"status": "stopped", "message": "Bot stopped successfully."}
    elif current_bot_instance and not current_bot_instance.is_running:
        logger.info(" Bot déjà arrêté, nettoyage de l'instance.")
        current_bot_instance = None
        return {"status": "already_stopped", "message": "Bot was already stopped."}

    logger.warning("🤔 Aucun bot en cours d'exécution à arrêter.")
    return {"status": "not_running", "message": "No bot instance found to stop."}

@shared_task(name='bot_app.tasks.get_bot_status_task')
def get_bot_status_task():
    global current_bot_instance
    if current_bot_instance:
        return current_bot_instance.get_status()
    return {"is_running": False, "message": "No bot instance found."}
    
@shared_task(name='bot_app.tasks.get_bot_ohlc_task')
def get_bot_ohlc_task(last_n=20):
    global current_bot_instance
    if current_bot_instance:
        return current_bot_instance.get_ohlc_history(last_n=last_n)
    return []

@shared_task(name='bot_app.tasks.get_bot_trades_task')
def get_bot_trades_task(last_n=20):
    global current_bot_instance
    if current_bot_instance:
        return current_bot_instance.get_trade_history(last_n=last_n)
    return []

# Tâche pour mettre à jour les cookies. Le bot devra être redémarré.
@shared_task(name='bot_app.tasks.update_bot_cookies_task')
def update_bot_cookies_task(cookies_json_list, cookies_path="Trading_cookies.json"):
    logger.info("🍪 Tâche Celery 'update_bot_cookies_task' initiée.")
    # Pas besoin d'instance de bot ici, on modifie juste le fichier.
    # Mais si on voulait le faire "à chaud", ce serait plus complexe.
    dummy_bot_for_cookies = TradingBot(cookies_path=cookies_path) # Juste pour utiliser la méthode
    dummy_bot_for_cookies.update_cookies(cookies_json_list)
    return {"status": "cookies_updated", "message": f"Cookies file {cookies_path} updated. Bot restart required."}