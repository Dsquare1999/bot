import base64
import json
import random
import time
import pandas as pd
from datetime import datetime, timedelta
import pytz
import logging
import os

import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
# from selenium.webdriver.chrome.service import Service # Potentiellement nécessaire selon l'install
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# from stock_indicators import indicators # Assure-toi que c'est le bon import
# from stock_indicators.indicators.common.quote import Quote # Vérifie si c'est utilisé

# Configure logging
logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, cookies_path="Trading_cookies.json", config=None):
        logger.info("🚀 Initialisation du TradingBot Dieu-Donnee...")
        self.cookies_path = cookies_path
        self.config = config if config else self._load_default_config()

        # Initialisation des variables d'état (anciennement globales)
        self.period_seconds = self.config.get("PERIOD", 0) # Secondes par bougie sur le graphe
        self.candles_history = [] # Stockera les objets Quote pour stock_indicators si besoin
        self.actions_log = {}
        self.max_actions_allowed = self.config.get("MAX_ACTIONS", 1)
        self.actions_relevancy_seconds = self.config.get("ACTIONS_SECONDS", self.period_seconds)
        self.last_ui_refresh_time = datetime.now() # Pour la gestion UI si besoin
        self.selected_currency_pair = None
        self.is_currency_changing = False # Flag pour gérer les changements de devise
        self.current_active_currency = None
        self.last_currency_change_time = datetime.now()

        self.companies_map = self.config.get("COMPANIES", {})
        self.currencies_map = self.config.get("CURRENCIES", {})

        self.ohlc_data = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Color", "Timestamp"])
        self.price_history_stream = pd.DataFrame(columns = ["Time", "Price"])
        
        self.trading_period_minutes = self.config.get("TRADING_PERIOD_MINUTES", 1) # Ex: 1 minute pour les bougies
        self.current_bet_index = 0
        self.bet_size_tiers = self.config.get("BET_SIZES", [1, 2, 5])
        self.active_bet_details = None # Infos sur le pari en cours
        self.trade_history_log = []
        self.is_trade_active_now = False # Si une condition de trade est rencontrée
        self.trading_offset_candles = self.config.get("OFFSET_CANDLES", 2) # Nombre de bougies identiques pour trader
        
        self.timezone = pytz.timezone(self.config.get("TIMEZONE", 'Etc/GMT-2'))
        self.current_candle_start_time = None
        self.current_candle_end_time = None

        self.driver = None
        self.is_running = False
        self._initialize_timestamps()
        logger.info("🤖 TradingBot initialisé avec la configuration : %s", self.config)

    def _load_default_config(self):
        """
        ⚙️ Charge la configuration par défaut si aucune n'est fournie.
        @returns {dict} - La configuration par défaut.
        """
        return {
            "PERIOD": 0, # Exemple, à ajuster
            "MAX_ACTIONS": 1,
            "COMPANIES": {
                'Apple OTC': '#AAPL_otc',
                'American Express OTC': '#AXP_otc',
                'Boeing Company OTC': '#BA_otc',
                'Johnson & Johnson OTC': '#JNJ_otc',
                "McDonald's OTC": '#MCD_otc',
                'Tesla OTC': '#TSLA_otc',
                'Amazon OTC': 'AMZN_otc',
                'VISA OTC': 'VISA_otc',
                'Netflix OTC': 'NFLX_otc',
                'Alibaba OTC': 'BABA_otc',
                'ExxonMobil OTC': '#XOM_otc',
                'FedEx OTC': 'FDX_otc',
                'FACEBOOK INC OTC': '#FB_otc',
                'Pfizer Inc OTC': '#PFE_otc',
                'Intel OTC': '#INTC_otc',
                'TWITTER OTC': 'TWITTER_otc',
                'Microsoft OTC': '#MSFT_otc',
                'Cisco OTC': '#CSCO_otc',
                'Citigroup Inc OTC': 'CITI_otc',
            },
            "CURRENCIES": {
                "AED/CNY": "AEDCNY",
                "AED/CNY OTC": "AEDCNY_otc",
                "AUD/CAD": "AUDCAD",
                "AUD/CAD OTC": "AUDCAD_otc",
                "AUD/CHF": "AUDCHF",
                "AUD/CHF OTC": "AUDCHF_otc",
                "AUD/JPY": "AUDJPY",
                "AUD/JPY OTC": "AUDJPY_otc",
                "AUD/NZD": "AUDNZD",
                "AUD/NZD OTC": "AUDNZD_otc",
                "AUD/USD": "AUDUSD",
                "AUD/USD OTC": "AUDUSD_otc",
                "BHD/CNY": "BHDCNY",
                "BHD/CNY OTC": "BHDCNY_otc",
                "CAD/CHF": "CADCHF",
                "CAD/CHF OTC": "CADCHF_otc",
                "CAD/JPY": "CADJPY",
                "CAD/JPY OTC": "CADJPY_otc",
                "CHF/JPY": "CHFJPY",
                "CHF/JPY OTC": "CHFJPY_otc",
                "CHF/NOK": "CHFNOK",
                "CHF/NOK OTC": "CHFNOK_otc",
                "EUR/AUD": "EURAUD",
                "EUR/CAD": "EURCAD",
                "EUR/CHF": "EURCHF",
                "EUR/CHF OTC": "EURCHF_otc",
                "EUR/GBP": "EURGBP",
                "EUR/GBP OTC": "EURGBP_otc",
                "EUR/HUF": "EURHUF",
                "EUR/HUF OTC": "EURHUF_otc",
                "EUR/JPY": "EURJPY",
                "EUR/JPY OTC": "EURJPY_otc",
                "EUR/NZD": "EURNZD",
                "EUR/NZD OTC": "EURNZD_otc",
                "EUR/RUB": "EURRUB",
                "EUR/RUB OTC": "EURRUB_otc",
                "EUR/TRY": "EURTRY",
                "EUR/TRY OTC": "EURTRY_otc",
                "EUR/USD": "EURUSD",
                "EUR/USD OTC": "EURUSD_otc",
                "GBP/AUD": "GBPAUD",
                "GBP/AUD OTC": "GBPAUD_otc",
                "GBP/CAD": "GBPCAD",
                "GBP/CHF": "GBPCHF",
                "GBP/JPY": "GBPJPY",
                "GBP/JPY OTC": "GBPJPY_otc",
                "GBP/USD": "GBPUSD",
                "GBP/USD OTC": "GBPUSD_otc",
                "JOD/CNY": "JODCNY",
                "JOD/CNY OTC": "JODCNY_otc",
                "LBP/USD": "LBPUSD",
                "LBP/USD OTC": "LBPUSD_otc",
                "MAD/USD": "MADUSD",
                "MAD/USD OTC": "MADUSD_otc",
                "NZD/JPY": "NZDJPY",
                "NZD/JPY OTC": "NZDJPY_otc",
                "NZD/USD": "NZDUSD",
                "NZD/USD OTC": "NZDUSD_otc",
                "OMR/CNY": "OMRCNY",
                "OMR/CNY OTC": "OMRCNY_otc",
                "QAR/CNY": "QARCNY",
                "QAR/CNY OTC": "QARCNY_otc",
                "SAR/CNY": "SARCNY",
                "SAR/CNY OTC": "SARCNY_otc",
                "TND/USD": "TNDUSD",
                "TND/USD OTC": "TNDUSD_otc",
                "USD/ARS": "USDARS",
                "USD/ARS OTC": "USDARS_otc",
                "USD/BDT": "USDBDT",
                "USD/BDT OTC": "USDBDT_otc",
                "USD/BRL": "USDBRL",
                "USD/BRL OTC": "USDBRL_otc",
                "USD/CAD": "USDCAD",
                "USD/CAD OTC": "USDCAD_otc",
                "USD/CHF": "USDCHF",
                "USD/CHF OTC": "USDCHF_otc",
                "USD/CLP": "USDCLP",
                "USD/CLP OTC": "USDCLP_otc",
                "USD/CNH": "USDCNH",
                "USD/CNH OTC": "USDCNH_otc",
                "USD/COP": "USDCOP",
                "USD/COP OTC": "USDCOP_otc",
                "USD/DZD": "USDDZD",
                "USD/DZD OTC": "USDDZD_otc",
                "USD/EGP": "USDEGP",
                "USD/EGP OTC": "USDEGP_otc",
                "USD/IDR": "USDIDR",
                "USD/IDR OTC": "USDIDR_otc",
                "USD/INR": "USDINR",
                "USD/INR OTC": "USDINR_otc",
                "USD/JPY": "USDJPY",
                "USD/JPY OTC": "USDJPY_otc",
                "USD/MXN": "USDMXN",
                "USD/MXN OTC": "USDMXN_otc",
                "USD/MYR": "USDMYR",
                "USD/MYR OTC": "USDMYR_otc",
                "USD/PHP": "USDPHP",
                "USD/PHP OTC": "USDPHP_otc",
                "USD/PKR": "USDPKR",
                "USD/PKR OTC": "USDPKR_otc",
                "USD/RUB": "USDRUB",
                "USD/RUB OTC": "USDRUB_otc",
                "USD/SGD": "USDSGD",
                "USD/SGD OTC": "USDSGD_otc",
                "USD/THB": "USDTHB",
                "USD/THB OTC": "USDTHB_otc",
                "USD/VND": "USDVND",
                "USD/VND OTC": "USDVND_otc",
                "YER/USD": "YERUSD",
                "YER/USD OTC": "YERUSD_otc"
            },
            "TRADING_PERIOD_MINUTES": 1,
            "BET_SIZES": [1, 2, 5], 
            "OFFSET_CANDLES": 2,
            "TIMEZONE": 'Etc/GMT-2',
            "BASE_URL": 'https://pocketoption.com',
            "CHROME_USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36", # Mettre à jour
            "SELENIUM_COMMAND_EXECUTOR": None, # Pourrait être "http://selenium-hub:4444/wd/hub" avec Selenium Grid
        }

    def _initialize_driver(self):
        """
        🚗 Initialise le driver Selenium. Peut être headless.
        """
        logger.info("🔧 Initialisation du driver Selenium...")
        options = Options()
        if self.config.get("HEADLESS", True): # Par défaut headless pour le serveur
            options.add_argument('--headless')
            options.add_argument('--disable-gpu') # Souvent nécessaire pour headless
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        if self.config.get("CHROME_USER_AGENT"):
            options.add_argument(f"user-agent={self.config['CHROME_USER_AGENT']}")
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})

        if self.config.get("SELENIUM_COMMAND_EXECUTOR"):
            logger.info("🌐 Connexion au Selenium Grid: %s", self.config["SELENIUM_COMMAND_EXECUTOR"])
            self.driver = webdriver.Remote(
                command_executor=self.config["SELENIUM_COMMAND_EXECUTOR"],
                options=options
            )
        else:
            # Assure-toi que chromedriver est dans le PATH ou spécifie le service
            # service = Service(executable_path='/path/to/chromedriver') # Si besoin
            # self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("🌐 Connexion au Selenium via Chrome")
            self.driver = webdriver.Chrome(options=options)
        
        self.driver.maximize_window()
        logger.info("✅ Driver Selenium initialisé.")

    def _clear_and_type_slowly(self, element, value):
        key_cmd = Keys.COMMAND if platform.system() == "Darwin" else Keys.CONTROL
        element.send_keys(key_cmd + "a")
        element.send_keys(Keys.BACKSPACE)
        time.sleep(0.2)
        element.send_keys(str(value))

    def _close_any_modal(self, driver, timeout=10, debug=False):
        wait = WebDriverWait(driver, timeout)

        selectors = [
            (By.CSS_SELECTOR, '.welcome-bonus-modal'),
            (By.CLASS_NAME, 'modal-close'),
            (By.CSS_SELECTOR, 'a.modal-close'),
            (By.XPATH, "//div[contains(@class, 'modal')]//a[contains(@class, 'close')]"),
            (By.XPATH, "//button[contains(text(), 'Close')]")
        ]

        for by, value in selectors:
            try:
                # Optionnel : prendre une capture d’écran à chaque tentative
                if debug:
                    ts = int(time.time())
                    screenshot_path = f"/app/screenshots/modal_debug_{ts}.png"
                    driver.save_screenshot(screenshot_path)
                    logger.debug(f"📸 Capture enregistrée : {screenshot_path}")

                # Suppression forcée des overlays bloquants
                try:
                    overlays = driver.find_elements(By.CLASS_NAME, "ReactModal__Overlay")
                    for overlay in overlays:
                        driver.execute_script("arguments[0].remove();", overlay)
                    logger.info("🧹 Tous les overlays supprimés via JavaScript.")
                except Exception as e:
                    logger.warning(f"⚠️ Impossible de supprimer les overlays : {e}")

                # Essayer de cliquer sur les éléments de fermeture
                element = wait.until(EC.element_to_be_clickable((by, value)))
                try:
                    element.click()
                    logger.info(f"✅ Click effectué sur le sélecteur {by} = {value}")
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", element)
                    logger.info(f"✅ Click forcé via JS sur {by} = {value}")
                except Exception as click_err:
                    logger.warning(f"⚠️ Erreur lors du clic sur {by} = {value} : {click_err}")
                
                return True  # Un modal a été fermé
            except TimeoutException:
                logger.debug(f"⏳ Aucun élément détecté pour {by} = {value}")
            except Exception as e:
                logger.warning(f"❌ Erreur inattendue pour {by} = {value} : {e}")

            time.sleep(1)  # pause avant d'essayer le suivant

        logger.info("🔍 Aucun pop-up modal pertinent trouvé.")
        return False
    
    def _load_cookies_and_navigate(self):
        """
        🍪 Charge les cookies et navigue vers la page de trading.
        """
        logger.info("🌍 Navigation vers: %s et chargement des cookies depuis %s", self.config["BASE_URL"], self.cookies_path)
        self.driver.get(self.config["BASE_URL"])
        self.driver.delete_all_cookies()

        try:
            with open(self.cookies_path, "r") as fichier:
                cookies_json = json.load(fichier)
            for cookie in cookies_json:
                cookie_data = {
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "path": cookie.get("path", "/"),
                    "domain": cookie.get("domain"), 
                    "secure": cookie.get("secure", False),
                    "httpOnly": cookie.get("httpOnly", False),
                }
                if "expiry" in cookie and cookie["expiry"] is not None:
                    cookie_data["expiry"] = int(cookie["expiry"])
                try:
                    self.driver.add_cookie(cookie_data)
                except Exception as e:
                    logger.warning("⚠️ Impossible d'ajouter le cookie %s: %s", cookie.get("name"), e)

        except FileNotFoundError:
            logger.error("❌ Fichier de cookies non trouvé: %s", self.cookies_path)
            raise
        except json.JSONDecodeError:
            logger.error("❌ Erreur de décodage JSON du fichier de cookies: %s", self.cookies_path)
            raise
        
        url = f'{self.config["BASE_URL"]}/en/cabinet/demo-quick-high-low/' # Configurable
        logger.info("🔄 Rechargement de la page avec les cookies: %s", url)
        self.driver.get(url)
        time.sleep(5) # Attendre que la page se charge bien

        for i in range(2):
            self._close_any_modal(driver=self.driver, timeout=10, debug=True)



    def _initialize_timestamps(self):
        """
        🕒 Initialise les horodatages de début et de fin de la bougie actuelle.
        """
        self.current_candle_start_time = datetime.now(self.timezone).replace(second=0, microsecond=0)
        if self.period_seconds > 0 and self.period_seconds < 60 : # Pour les périodes en secondes
            # Aligner sur le multiple de self.period_seconds le plus proche
            current_seconds = self.current_candle_start_time.second
            seconds_to_subtract = current_seconds % self.period_seconds
            self.current_candle_start_time = self.current_candle_start_time - timedelta(seconds=seconds_to_subtract)
            self.current_candle_end_time = self.current_candle_start_time + timedelta(seconds=self.period_seconds)

        else: # Pour les périodes en minutes
            self.current_candle_end_time = self.current_candle_start_time + timedelta(minutes=self.trading_period_minutes)
        logger.info("🕯️ Bougie initiale: START=%s, END=%s (Période: %s min ou %s sec)",
                    self.current_candle_start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    self.current_candle_end_time.strftime('%Y-%m-%d %H:%M:%S'),
                    self.trading_period_minutes,
                    self.period_seconds)


    def _set_position_amount(self, amount):
        try:
            # XPATH basé sur le bloc 'Amount'
            amount_input_xpath = "//div[contains(@class, 'block--bet-amount')]//input[@type='text']"
            timeout_seconds = 10
            logger.debug("💸 Attente de la visibilité de l'input de mise (Timeout: %s sec)...", timeout_seconds)

            wait = WebDriverWait(self.driver, timeout_seconds)
            logger.debug("💸 Attente 2 de l'input de mise...")

            # self._close_any_modal(driver=self.driver, timeout=5, debug=False)

            # time.sleep(1)
            logger.debug("Closing of any modal bypassed.")

            # Attente de l’input présent et cliquable
            wait.until(EC.presence_of_element_located((By.XPATH, amount_input_xpath)))
            bet_input = wait.until(EC.element_to_be_clickable((By.XPATH, amount_input_xpath)))

            logger.info("✅ Input trouvé, mise à jour du montant : %s", amount)
            self._clear_and_type_slowly(bet_input, amount)

            final_value = bet_input.get_attribute("value")
            logger.info("🔎 Valeur finale dans l'input : %s", final_value)

        except Exception as e:
            logger.error("❌ Erreur lors de la définition du montant : %s", str(e))
            raise



    def _get_current_yield_and_select_best(self):
        """
            📈 Vérifie le rendement actuel et sélectionne la meilleure devise si le rendement n'est pas de +92%.
            @returns {bool} - True si le rendement est OK ou si une meilleure devise a été sélectionnée, False sinon.
        """
        try:
            logger.debug("🔍 Vérification du rendement actuel...")

            current_percent_element = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'block--payout')]//div[contains(@class, 'value__val-start')]")))
            current_percent_text = current_percent_element.text.strip()
            
            logger.info("📊 Rendement actuel affiché : %s", current_percent_text)

            if current_percent_text != "+92%": 
                logger.warning("📉 Rendement (%s) non optimal. Tentative de changement de devise.", current_percent_text)
                self._reset_trade_state() # Réinitialiser l'état de trading

                # Clique sur le bloc de devise
                currency_div = self.driver.find_element(By.CSS_SELECTOR, ".currencies-block__in")
                currency_div.click()
                logger.info("🔄 Bloc de devise cliqué pour ouvrir la liste des devises.")
                time.sleep(1)

                # Clique sur l’onglet "Currencies"
                currency_tab = self.driver.find_element(By.CSS_SELECTOR, ".assets-block__nav-item--currency")
                currency_tab.click()
                logger.info("🔄 Onglet 'Currencies' cliqué pour afficher la liste des devises.")
                time.sleep(1)

                # Recherche de la première devise avec +92%
                # Les XPATHs ici sont très fragiles et dépendent de la structure de la page.
                # Il est préférable de boucler sur les éléments de la liste.
                try:
                    logger.info("🔍 Recherche de la meilleure devise avec +92%% de rendement...")
                    # currency_list_items = self.driver.find_elements(By.XPATH, "/html/body/div[9]/div/div/div/div[2]/div[2]/div/div/div[1]/ul/li")
                    currency_list = WebDriverWait(self.driver, 10).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "ul.alist-currency > li.alist__item")))
                    found_best_currency = False
                    for item_li in currency_list:
                        try:
                            logger.debug("🔎 Traitement de l'item de devise: %s", item_li.text)
                            label_element = item_li.find_element(By.XPATH, ".//a/span[3]") # Nom de la devise
                            yield_element = item_li.find_element(By.XPATH, ".//a/span[4]/span") # Rendement
                            logger.debug("Devise: %s, Rendement: %s", label_element.text, yield_element.text)

                            if yield_element.text == "+92%":
                                currency_name_on_site = label_element.text
                                if currency_name_on_site in self.currencies_map:
                                    self.current_active_currency = self.currencies_map[currency_name_on_site]
                                    logger.info("✅ Meilleure devise trouvée : %s (%s) avec rendement %s", currency_name_on_site, self.current_active_currency, yield_element.text)
                                    item_li.click() # Sélectionner cette devise
                                    time.sleep(1)
                                    # Fermer le modal de sélection de devise (souvent avec Echap ou un bouton croix)
                                    # self.driver.find_element(By.XPATH, "/html/body/div[9]/div/div/div/div[2]/div[1]/div[1]/input").send_keys(Keys.ESCAPE) # Champ de recherche, puis Echap
                                    search_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.search__field")))
                                    search_input.send_keys(Keys.ESCAPE) # Fermer le champ de recherche
                                    logger.info("🔄 Modal de sélection de devise fermé.")
                                    found_best_currency = True
                                    self.is_currency_changing = True # Indiquer qu'un changement a eu lieu
                                    self.last_currency_change_time = datetime.now()
                                    logger.info("🔄 Devise active mise à jour: %s", self.current_active_currency)
                                    break 
                                else:
                                    logger.warning("⚠️ Devise %s avec +92%% non trouvée dans currencies_map.", currency_name_on_site)
                        except Exception as e_item:
                            logger.debug("Erreur mineure lors de l'itération sur un item de devise: %s", e_item)
                            continue
                    
                    if not found_best_currency:
                        logger.error("❌ Aucune devise avec +92%% de rendement trouvée ou mappée.")
                        # Fermer le modal quand même
                        try:
                            # self.driver.find_element(By.XPATH, "/html/body/div[9]/div/div/div/div[2]/div[1]/div[1]/input").send_keys(Keys.ESCAPE)
                            search_input = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.search__field")))
                            search_input.send_keys(Keys.ESCAPE)
                            logger.info("Modal de sélection de devise fermé.")
                        except: 
                            logger.error("❌ Impossible de fermer le modal de sélection de devise.")
                        return False
                except Exception as e_list:
                    logger.error("❌ Erreur lors de la recherche de la meilleure devise: %s", e_list)
                    # self.save_debug_screenshot("get_yield_error")
                    return False
            else: # Rendement déjà à +92%
                # Vérifier si la devise actuelle est correctement enregistrée
                # logger.info("✅ Rendement actuel est déjà optimal: %s", current_percent_text)
                # current_label_element = self.driver.find_element(By.XPATH, "/html/body/div[4]/div[2]/div[3]/div/div/div/div[1]/div/div[1]/div[1]/div[1]/div/a/div/span")
                # current_currency_name_on_site = current_label_element.text

                current_label_element = self.driver.find_element(By.CSS_SELECTOR, "span.current-symbol.current-symbol_cropped")
                current_currency_name_on_site = current_label_element.text
                logger.info("✅ Rendement actuel est déjà optimal: %s", current_currency_name_on_site)
                if current_currency_name_on_site in self.currencies_map:
                    logger.info("🔍 Devise actuelle sur le site: %s", current_currency_name_on_site)
                    mapped_code = self.currencies_map[current_currency_name_on_site]
                    if self.current_active_currency != mapped_code:
                        logger.info("🔄 Synchronisation de la devise active: %s -> %s", self.current_active_currency, mapped_code)
                        self._reset_trade_state() # Important si la devise a changé sans qu'on le sache
                        self.current_active_currency = mapped_code
                        self.is_currency_changing = True
                        self.last_currency_change_time = datetime.now()
                else:
                    logger.warning("⚠️ Devise actuelle %s non trouvée dans currencies_map. Risque de désynchronisation.", current_currency_name_on_site)
                    self.current_active_currency = None # Forcer une re-sélection au prochain cycle peut-être
                    return False # Pourrait indiquer un problème

            logger.info("➡️ Devise active pour le trading: %s", self.current_active_currency)
            return True

        except Exception as e:
            logger.error("❌ Erreur critique dans _get_current_yield_and_select_best: %s", e)
            # self.save_debug_screenshot("critical_yield_error")
            return False

    def _get_candle_color(self, open_price, close_price):
        """
        🎨 Détermine la couleur de la bougie.
        @returns {str} - "green" ou "red".
        """
        return "green" if close_price > open_price else "red"

    def _set_trade_timeout(self, minutes=1):
        """
        ⏱️ Configure le délai d'expiration du trade. (Adapté de ton code)
        @param {int} minutes - Le nombre de minutes pour l'expiration.
        """
        try:
            logger.debug("⏳ Configuration du délai d'expiration à %s minute(s)...", minutes)
            # Clique sur l'icône pour changer le mode d'expiration si nécessaire
            svg_element = self.driver.find_element(By.CSS_SELECTOR, "#put-call-buttons-chart-1 > div > div.blocks-wrap > div.block.block--expiration-inputs > div.block__control.control > div.control-buttons__wrapper > div > a > div > div > svg")
            if svg_element.get_attribute("data-src") != "/themes/cabinet/svg/icons/trading-panel/exp-mode-2.svg":
                svg_element.click()
                time.sleep(0.5) # Attente de l'ouverture du modal

            # Configuration du temps dans le modal
            # Les XPATH/CSS Selectors sont spécifiques à l'UI de PocketOption et peuvent casser.
            # Boucle pour gérer les cas où le modal n'est pas immédiatement prêt
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    hour_input = self.driver.find_element(By.CSS_SELECTOR, "#modal-root > div > div > div > div.trading-panel-modal__in > div:nth-child(1) > div > input")
                    hour_input.click()
                    hour_input.send_keys(Keys.CONTROL + "a")
                    hour_input.send_keys(Keys.BACKSPACE)
                    hour_input.send_keys(Keys.BACKSPACE)
                
                    minute_plus=self.driver.find_element(By.CSS_SELECTOR,"#modal-root > div > div > div > div.trading-panel-modal__in > div:nth-child(2) > a.btn-plus")
                    for i in range(minutes):
                        minute_plus.click()
                    
                    seconde_input = self.driver.find_element(By.CSS_SELECTOR, "#modal-root > div > div > div > div.trading-panel-modal__in > div:nth-child(3) > div > input")
                    seconde_input.click()  
                    seconde_input.send_keys(Keys.CONTROL + "a")  # sélectionne tout
                    seconde_input.send_keys("00")               # tape la nouvelle valeur
                    auto_open=self.driver.find_element(By.XPATH,'//*[@id="modal-root"]/div/div/div/div[2]/div/label')

                    class_attr=auto_open.get_attribute('class')
                    if 'is-checked' not in class_attr:
                        auto_incl=self.driver.find_element(By.CSS_SELECTOR,'#modal-root > div > div > div > div.trading-panel-modal__dops.dops.dops-with-timeframes > div > label > div.mdl-switch__thumb > span')
                        auto_incl.click()
                        select_time=self.driver.find_element(By.CSS_SELECTOR,'#modal-root > div > div > div > div.trading-panel-modal__dops.dops.dops-with-timeframes.opened > div.dops__timeframes > div:nth-child(2)')
                        select_time.click()
                    
                    time_input.click()
                    logger.info("✅ Délai d'expiration configuré.")
                    break # Sortir de la boucle retry
                except Exception as e_modal:
                    # logger.warning("Problème lors de la configuration du délai d'expiration: %s", e_modal)
                    # time_input = self.driver.find_element(By.XPATH, "/html/body/div[4]/div[2]/div[3]/div/div/div/div[1]/div/div[5]/div/div/div[2]/div/div[1]/div[1]/div[2]/div[1]")
                    time_input = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.control__value.value.value--several-items")))
                    time_input.click()


            
            # S'assurer que le modal est fermé, par exemple en cliquant sur le body
            # self.driver.find_element(By.TAG_NAME, "body").click()
            # Ou en envoyant Echap au champ principal de mise
            # bet_input_main = self.driver.find_element(By.XPATH,"/html/body/div[4]/div[2]/div[3]/div/div/div/div[1]/div/div[5]/div/div/div[2]/div/div[1]/div[2]/div[2]/div[1]/div/input")
            # bet_input_main.send_keys(Keys.ESCAPE)
            bet_input_main = self.driver.find_element(By.CSS_SELECTOR, "div.block--bet-amount input[type='text']")
            bet_input_main.send_keys(Keys.ESCAPE)


        except Exception as e:
            logger.error("❌ Erreur critique dans _set_trade_timeout: %s", e)
            # self.save_debug_screenshot("critical_timeout_error")
            raise

    def _timestamp_to_human_readable(self, timestamp, timezone_offset=0):
        if timestamp > 1e12:
            timestamp /= 1000

        dt = datetime.utcfromtimestamp(timestamp)
        dt = dt.replace(hour=dt.hour + timezone_offset)
        local_dt = dt.astimezone(self.timezone)
        return local_dt
        # return dt.strftime('%Y-%m-%d %H:%M:%S')

    def get_current_balance(self):
        """
        🏦 Récupère le solde actuel du compte.
        @returns {float|None} - Le solde, ou None en cas d'erreur.
        """
        try:
            balance_element = self.driver.find_element(By.XPATH,"/html/body/div[4]/div[1]/header/div[3]/div[3]/div/div[2]/div[1]/span")
            balance_text = balance_element.text.replace('$', '').replace(',', '').strip() # Nettoyer le formatage
            logger.info("💰 Solde actuel: %s", balance_text)
            return float(balance_text)
        except Exception as e:
            logger.error("❌ Erreur lors de la récupération du solde: %s", e)
            # self.save_debug_screenshot("get_balance_error")
            return None

    def _take_position(self, direction_color):
        """
        🚀 Place un ordre (CALL pour green, PUT pour red).
        @param {str} direction_color - "green" (achat/CALL) ou "red" (vente/PUT).
        """
        try:
            if direction_color == 'green':
                selector = "div.button-call-wrap a.btn-call"
                logger.info("⬆️ Placement d'un ordre CALL (green)...")
            elif direction_color == 'red':
                selector = "div.button-put-wrap a.btn-put"
                logger.info("⬇️ Placement d'un ordre PUT (red)...")
            else:
                logger.error("❌ Couleur de direction invalide pour _take_position: %s", direction_color)
                return

            # Attendre que le bouton soit cliquable (meilleure stabilité)
            position_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, selector)))
            position_button.click()

            self.actions_log[datetime.now()] = {
                "direction": direction_color,
                "amount": self.active_bet_details['amount'] if self.active_bet_details else "N/A"
            }

            logger.info("✅ Ordre %s placé.", direction_color.upper())

        except Exception as e:
            logger.error("❌ Erreur lors de la prise de position (%s): %s", direction_color, e)
            # self.save_debug_screenshot(f"take_position_{direction_color}_error")

    def _apply_trade_logic(self, last_formed_candle_color):
        """
        🧠 Applique la logique de trading basée sur la couleur de la dernière bougie formée.
        @param {str} last_formed_candle_color - "green" ou "red".
        """
        logger.debug("🚦 Application de la logique de trading avec la dernière bougie: %s", last_formed_candle_color)
        
        # Vérifier si on a assez de bougies pour la logique d'offset
        if len(self.ohlc_data) < self.trading_offset_candles:
            logger.debug("📉 Pas assez de bougies (%s/%s) pour la logique d'offset. Attente...", len(self.ohlc_data), self.trading_offset_candles)
            return

        last_colors = list(self.ohlc_data['Color'].tail(self.trading_offset_candles))
        logger.info("📊 Dernières %s couleurs de bougies: %s", self.trading_offset_candles, last_colors)

        # Condition pour initier une série de trades
        if not self.is_trade_active_now and len(set(last_colors)) == 1:
            self.is_trade_active_now = True
            logger.info("▶️ Condition de trade (série de %s %s) rencontrée. Activation de la séquence de trading.", self.trading_offset_candles, last_colors[0])
            self.current_bet_index = 0 # Réinitialiser l'index de mise au début d'une nouvelle série
        
        # Si une série de trades est active
        if self.is_trade_active_now:
            target_trade_color = last_colors[0] # On trade dans le sens de la série
            
            # Vérifier la synchro de la devise et le rendement
            # Cette fonction peut changer self.current_active_currency et self.is_currency_changing
            if not self._get_current_yield_and_select_best():
                logger.warning("🚫 Impossible d'assurer un bon rendement ou une bonne devise. Trading suspendu pour ce cycle.")
                self.is_trade_active_now = False # Peut-être désactiver la série
                self._reset_trade_state()
                return
            
            # Si la devise a changé, on saute ce cycle de trading pour laisser le temps à la nouvelle devise de charger ses données
            if self.is_currency_changing:
                if (datetime.now() - self.last_currency_change_time).total_seconds() < (self.period_seconds * 2 if self.period_seconds > 0 else self.trading_period_minutes * 60 * 2): # Attendre au moins 2 périodes
                    logger.info("⏳ Changement de devise récent. Attente de stabilisation des données pour %s.", self.current_active_currency)
                    # Ne pas réinitialiser is_trade_active_now ici, on veut continuer la série sur la nouvelle devise si possible
                    return 
                else:
                    self.is_currency_changing = False # Stabilisation supposée terminée

            # Logique de Martingale / gestion des mises
            if self.active_bet_details is None: # Premier trade de la série ou après une victoire
                self.current_bet_index = 0
                current_bet_amount = self.bet_size_tiers[self.current_bet_index]
                self._set_position_amount(current_bet_amount)
                self.active_bet_details = {'color_traded': target_trade_color, 'amount': current_bet_amount, 'expected_close_time': self.current_candle_end_time + timedelta(minutes=self.trading_period_minutes)} # Ou une autre logique pour l'heure de fermeture
                self._take_position(target_trade_color)
                logger.info(" TRADE #1 (Série %s): %s de %s. Prochain montant préparé: %s", 
                            target_trade_color, target_trade_color.upper(), current_bet_amount, 
                            self.bet_size_tiers[self.current_bet_index + 1] if self.current_bet_index + 1 < len(self.bet_size_tiers) else "N/A")
                # Préparer le montant pour le prochain trade potentiel (Martingale)
                if self.current_bet_index + 1 < len(self.bet_size_tiers):
                    self._set_position_amount(self.bet_size_tiers[self.current_bet_index + 1])
            
            else: # Un trade précédent est en cours ou vient de se terminer
                # Ici, il faut déterminer si le trade précédent a gagné ou perdu.
                # PocketOption ne donne pas un feedback direct via WebSocket pour ça.
                # La méthode la plus simple est de supposer que le trade s'est terminé à la fin de la bougie précédente
                # et de comparer la couleur tradée avec la couleur de CETTE bougie.
                previous_traded_color = self.active_bet_details['color_traded']
                win = (last_formed_candle_color == previous_traded_color)
                self.trade_history_log.append({
                    "timestamp": datetime.now(self.timezone),
                    "traded_color": previous_traded_color,
                    "amount": self.active_bet_details['amount'],
                    "outcome_candle_color": last_formed_candle_color,
                    "result": "WIN" if win else "LOSS"
                })

                if win:
                    logger.info("🎉 VICTOIRE ! Le trade %s de %s a gagné. (Bougie de résultat: %s)", previous_traded_color.upper(), self.active_bet_details['amount'], last_formed_candle_color)
                    self.current_bet_index = 0 # Réinitialiser la Martingale
                    current_bet_amount = self.bet_size_tiers[self.current_bet_index]
                    self._set_position_amount(current_bet_amount) # Mise de base
                    self.active_bet_details = {'color_traded': target_trade_color, 'amount': current_bet_amount, 'expected_close_time': self.current_candle_end_time + timedelta(minutes=self.trading_period_minutes)}
                    self._take_position(target_trade_color) # Nouveau trade avec la mise de base
                    logger.info("  RE-TRADE (Série %s): %s de %s. Prochain montant: %s", 
                                target_trade_color, target_trade_color.upper(), current_bet_amount,
                                self.bet_size_tiers[self.current_bet_index + 1] if self.current_bet_index + 1 < len(self.bet_size_tiers) else "N/A")
                    if self.current_bet_index + 1 < len(self.bet_size_tiers):
                         self._set_position_amount(self.bet_size_tiers[self.current_bet_index + 1])

                else: # Perte
                    logger.warning("ኪ PERTE. Le trade %s de %s a perdu. (Bougie de résultat: %s)", previous_traded_color.upper(), self.active_bet_details['amount'], last_formed_candle_color)
                    self.current_bet_index += 1
                    if self.current_bet_index < len(self.bet_size_tiers): # Martingale continue
                        current_bet_amount = self.bet_size_tiers[self.current_bet_index]
                        # Le montant a déjà été setté (normalement)
                        self.active_bet_details = {'color_traded': target_trade_color, 'amount': current_bet_amount, 'expected_close_time': self.current_candle_end_time + timedelta(minutes=self.trading_period_minutes)}
                        self._take_position(target_trade_color)
                        logger.info("  MARTINGALE TRADE #%s (Série %s): %s de %s. Prochain montant: %s", 
                                    self.current_bet_index + 1, target_trade_color, target_trade_color.upper(), current_bet_amount,
                                    self.bet_size_tiers[self.current_bet_index + 1] if self.current_bet_index + 1 < len(self.bet_size_tiers) else self.bet_size_tiers[0]) # Prépare le suivant ou revient au début
                        if self.current_bet_index + 1 < len(self.bet_size_tiers):
                            self._set_position_amount(self.bet_size_tiers[self.current_bet_index + 1])
                        else: # Fin de la Martingale, retour au début
                            self._set_position_amount(self.bet_size_tiers[0])

                    else: # Plafond de Martingale atteint
                        logger.error("🛑 PLAFOND DE MARTINGALE ATTEINT (%s étapes). Arrêt de la série de trades.", len(self.bet_size_tiers))
                        self.is_trade_active_now = False
                        self._reset_trade_state()
                        self._set_position_amount(self.bet_size_tiers[0]) # Réinitialiser au montant de base
        else: # Pas de condition de trade active
            if self.active_bet_details: # S'il y avait un trade en cours qui vient de se finir (hors série)
                # Cette logique est pour un trade unique, pas couvert par ta stratégie d'offset, mais bon à avoir
                previous_traded_color = self.active_bet_details['color_traded']
                win = (last_formed_candle_color == previous_traded_color)
                logger.info("Trade unique terminé: %s. Résultat: %s", previous_traded_color, "WIN" if win else "LOSS")
                self._reset_trade_state() # Nettoyer après un trade unique

    def _reset_trade_state(self):
        """
        🔄 Réinitialise l'état de trading (index de mise, détails du pari).
        """
        logger.info("🔄 Réinitialisation de l'état de trading.")
        self.current_bet_index = 0
        self.active_bet_details = None
        # self.is_trade_active_now = False # Ne pas forcément le faire ici, car _apply_trade_logic le gère
        # self.ohlc_data = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Color", "Timestamp"]) # Peut-être pas réinitialiser OHLC complet
        # self.price_history_stream = pd.DataFrame(columns = ["Time", "Price"]) # Idem
        self._set_position_amount(self.bet_size_tiers[0]) # Assurer que le montant est au minimum
        self._initialize_timestamps() # Réinitialiser les timers de bougie aussi

    def _process_websocket_data(self):
        """
        📡 Traite les messages WebSocket récupérés des logs de performance du navigateur.
        """
        if not self.driver:
            logger.warning("Driver non initialisé, impossible de récupérer les logs WebSocket.")
            return

        if not self.current_active_currency:
            logger.debug("Pas de devise active sélectionnée, en attente de _get_current_yield_and_select_best.")
            # Tentative de sélection pour démarrer
            if not self._get_current_yield_and_select_best():
                logger.warning("Impossible de sélectionner une devise, le traitement WebSocket est en pause.")
                time.sleep(5) # Attendre avant de réessayer
                return
            else: # Devise sélectionnée, on peut continuer
                 self._initialize_timestamps() # S'assurer que les timestamps sont frais pour la nouvelle devise
                 self.price_history_stream = pd.DataFrame(columns = ["Time", "Price"]) # Vider l'historique de prix de l'ancienne devise
                 self.ohlc_data = pd.DataFrame(columns=["Open", "High", "Low", "Close", "Color", "Timestamp"]) # Vider OHLC

        try:
            logs = self.driver.get_log('performance')
            logger.debug("Logs de performance:")
        except Exception as e:
            logger.error("❌ Erreur lors de la récupération des logs de performance: %s", e)
            return

        for wsData_entry in logs:
            try:
                logger.debug("Message WebSocket reçu")
                message_data = json.loads(wsData_entry['message'])['message']
                response_data = message_data.get('params', {}).get('response', {})

                if response_data.get('opcode', 0) == 2: # Message binaire
                    logger.debug("Opcode 0 logging message")
                    payload_str_b64 = response_data.get('payloadData')
                    if not payload_str_b64:
                        continue

                    logger.debug("playload bytes message")
                    payload_bytes = base64.b64decode(payload_str_b64)
                    
                    # Tenter de décoder en UTF-8. Si ça échoue, c'est peut-être un autre format ou compressé.
                    # PocketOption utilise souvent du JSON simple non compressé pour les ticks.
                    try:
                        payload_str = payload_bytes.decode('utf-8')
                        logger.debug("playload decoding byte messages")

                    except UnicodeDecodeError:
                        logger.debug("Unicode decode error")
                        continue # Ignorer les messages non décodables pour l'instant

                    try:
                        data = json.loads(payload_str)
                        logger.debug("Datalog payload string")

                    except json.JSONDecodeError:
                        # logger.debug("Impossible de décoder le payload JSON: %s", payload_str[:100]) # Log début du payload
                        logger.debug("Impossible to decode payload JSON")
                        continue
                    
                    # Filtrer pour les données de prix de la devise active
                    # Le format est souvent: [["EURUSD_otc",1678886400000,1.06659]] ou similaire
                    if isinstance(data, list) and len(data) > 0 and \
                       isinstance(data[0], list) and len(data[0]) == 3 and \
                       isinstance(data[0][0], str) and data[0][0] == self.current_active_currency:
                        
                        logger.debug("Filter money price data ")
                        
                        timestamp_ms = data[0][1]
                        price = data[0][2]
                        
                        dt_object = self._timestamp_to_human_readable(timestamp_ms)

                        new_price_tick = pd.DataFrame({
                            "Time": [dt_object], # Utiliser l'objet datetime directement
                            "Price": [price]
                        })
                        self.price_history_stream = pd.concat([self.price_history_stream, new_price_tick], ignore_index=True)
                        logger.debug("Tick reçu 1 - > - - - ")

                        # Construction des bougies OHLC
                        # Assurer que price_history_stream a 'Time' comme index pour le resample
                        if not self.price_history_stream.empty and 'Time' in self.price_history_stream.columns:
                            logger.debug("Tick reçu 2 - > - - - ")

                            df_for_ohlc = self.price_history_stream.set_index('Time')

                            logger.info("DEBUG df_for_ohlc", df_for_ohlc)
                            
                            # Vérifier si la bougie actuelle est terminée
                            # current_time_aware = datetime.now(self.timezone)
                            # Utiliser le temps du dernier tick reçu pour être plus précis
                            current_tick_time_aware = dt_object 
                            logger.debug("DEBUG current_candle_end_time %s", self.current_candle_end_time)
                            logger.debug("DEBUG current_tick_time_aware %s", current_tick_time_aware)

                            # if self.current_candle_end_time and pd.to_datetime(current_tick_time_aware) >= self.current_candle_end_time:
                            if self.current_candle_end_time and current_tick_time_aware >= self.current_candle_end_time:
                                logger.info("🕯️ Fermeture de la bougie: %s à %s", 
                                            self.current_candle_start_time.strftime('%H:%M:%S'), 
                                            self.current_candle_end_time.strftime('%H:%M:%S'))

                                logger.debug("Bougie terminee")

                                # Sélectionner les ticks pour la bougie qui vient de se terminer
                                candle_ticks = df_for_ohlc[(df_for_ohlc.index >= self.current_candle_start_time) & 
                                                           (df_for_ohlc.index < self.current_candle_end_time)]
                                
                                logger.debug("Candle ticks:\n%s", candle_ticks)

                                if not candle_ticks.empty:
                                    open_price = candle_ticks['Price'].iloc[0]
                                    high_price = candle_ticks['Price'].max()
                                    low_price = candle_ticks['Price'].min()
                                    close_price = candle_ticks['Price'].iloc[-1]
                                    candle_color = self._get_candle_color(open_price, close_price)
                                    
                                    new_ohlc_row = pd.DataFrame({
                                        "Open": [open_price], "High": [high_price], 
                                        "Low": [low_price], "Close": [close_price], 
                                        "Color": [candle_color], "Timestamp": [self.current_candle_start_time] # Heure d'ouverture de la bougie
                                    })
                                    self.ohlc_data = pd.concat([self.ohlc_data, new_ohlc_row], ignore_index=True)
                                    
                                    logger.info("Nouvelle bougie OHLC (%s): O:%.5f H:%.5f L:%.5f C:%.5f Couleur:%s", 
                                                self.current_candle_start_time.strftime('%H:%M'),
                                                open_price, high_price, low_price, close_price, candle_color)
                                    # logger.debug("OHLC Data:\n%s", self.ohlc_data.tail())

                                    # Appliquer la logique de trading
                                    self._apply_trade_logic(candle_color)

                                else:
                                    logger.warning("⚠️ Aucune donnée de tick pour la bougie de %s à %s.", 
                                                   self.current_candle_start_time.strftime('%H:%M:%S'), 
                                                   self.current_candle_end_time.strftime('%H:%M:%S'))
                                
                                # Mettre à jour pour la prochaine bougie
                                self.current_candle_start_time = self.current_candle_end_time
                                if self.period_seconds > 0 and self.period_seconds < 60:
                                    logger.debug("Tick reçu 3 - > - - - ")
                                    self.current_candle_end_time = self.current_candle_start_time + timedelta(seconds=self.period_seconds)
                                else:
                                    logger.debug("Tick reçu 4 - > - - - ")
                                    self.current_candle_end_time = self.current_candle_start_time + timedelta(minutes=self.trading_period_minutes)
                                logger.debug("Prochaine bougie attendue: %s à %s", self.current_candle_start_time.strftime('%H:%M:%S'), self.current_candle_end_time.strftime('%H:%M:%S'))
                                
                                # Nettoyer l'historique de prix pour ne pas qu'il grossisse indéfiniment
                                # Garder par exemple les 10 dernières minutes de ticks
                                max_history_time = timedelta(minutes=10) # Configurable
                                self.price_history_stream = self.price_history_stream[self.price_history_stream['Time'] > (datetime.now(self.timezone) - max_history_time)]

                    # D'autres types de messages WebSocket pourraient être gérés ici (ex: confirmation de trade, erreurs, etc.)
                    # Mais PocketOption est assez limité sur ce qu'il envoie en clair.

            except Exception as e_msg:
                # logger.debug("Erreur mineure lors du traitement d'un message WebSocket: %s", e_msg)
                logger.error("Error Tick reçu - > - - - %s", e_msg)
                # pass # Beaucoup de messages ne sont pas pertinents

    def start(self):
        """
        ▶️ Démarre le bot de trading.
        """
        if self.is_running:
            logger.warning("🚦 Le bot est déjà en cours d'exécution.")
            return

        logger.info("🏁 Démarrage du bot de trading Dieu-Donnee...")
        self.is_running = True
        try:
            self._initialize_driver()
            self._load_cookies_and_navigate()
            
            # Initialisation après chargement de la page
            self._reset_trade_state() # Assure un état propre et montant de base
            if not self._get_current_yield_and_select_best(): # Sélectionne la devise et vérifie le rendement
                logger.error("❌ Impossible de démarrer : Problème de sélection de devise ou de rendement.")
                self.stop()
                return
            
            self._set_trade_timeout(minutes=self.trading_period_minutes)

            logger.info("✅ Bot démarré et prêt à trader sur %s.", self.current_active_currency)

            self.save_debug_screenshot("timeout_error_set_amount") # On capture la preuve !

            # Boucle principale
            while self.is_running:
                self._process_websocket_data()
                # Petite pause pour ne pas surcharger le CPU avec get_log,
                # et pour laisser le temps aux messages WS d'arriver.
                # time.sleep(0.1) # Très court, car les ticks sont rapides. À ajuster.
        
        except Exception as e:
            logger.critical("💥 Erreur critique lors de l'exécution du bot: %s", e, exc_info=True)
            # self.save_debug_screenshot("critical_bot_error")
        finally:
            logger.info("🛑 Bot arrêté (ou a crashé).")
            self.stop() # Assurer un nettoyage propre

    def stop(self):
        """
        ⏹️ Arrête le bot de trading et nettoie le driver.
        """
        logger.info("🛑 Tentative d'arrêt du bot...")
        self.is_running = False
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Driver Selenium fermé.")
            except Exception as e:
                logger.error("❌ Erreur lors de la fermeture du driver: %s", e)
            self.driver = None
    
    def update_cookies(self, new_cookies_json_list):
        """
        🍪 Met à jour les cookies et les sauvegarde dans le fichier.
        @param {list} new_cookies_json_list - La nouvelle liste de cookies.
        """
        logger.info("📝 Mise à jour du fichier de cookies...")
        try:
            with open(self.cookies_path, "w", encoding="utf-8") as fichier:
                json.dump(new_cookies_json_list, fichier, ensure_ascii=False, indent=4)
            logger.info("✅ Fichier de cookies mis à jour : %s", self.cookies_path)
            # Si le bot tourne, il faudrait le redémarrer pour prendre en compte les nouveaux cookies.
            if self.is_running:
                logger.warning("⚠️ Les cookies ont été mis à jour. Un redémarrage du bot est nécessaire pour les appliquer.")
        except Exception as e:
            logger.error("❌ Erreur lors de la sauvegarde des nouveaux cookies: %s", e)

    def get_status(self):
        """
        ℹ️ Retourne l'état actuel du bot.
        @returns {dict} - Un dictionnaire contenant l'état.
        """
        return {
            "is_running": self.is_running,
            "current_active_currency": self.current_active_currency,
            "current_balance": self.get_current_balance() if self.driver and self.is_running else None,
            "active_bet_details": self.active_bet_details,
            "current_bet_index": self.current_bet_index,
            "is_trade_active_now": self.is_trade_active_now, # La condition de série est-elle active ?
            "last_ohlc_data_count": len(self.ohlc_data),
            "last_trade_log_count": len(self.trade_history_log),
            "next_candle_expected_close": self.current_candle_end_time.strftime('%Y-%m-%d %H:%M:%S') if self.current_candle_end_time else "N/A",
            "current_config": self.config # Pourrait être sélectif pour ne pas tout exposer
        }
        
    def get_ohlc_history(self, last_n=20):
        """
        📊 Retourne les N dernières bougies OHLC.
        """
        if self.ohlc_data.empty:
            return []
        return self.ohlc_data.tail(last_n).to_dict(orient='records')

    def get_trade_history(self, last_n=20):
        """
        📜 Retourne les N derniers trades enregistrés.
        """
        if not self.trade_history_log:
            return []
        return self.trade_history_log[-last_n:]
        
    # def save_debug_screenshot(self, filename_prefix="debug"):
    #     """
    #     📸 Sauvegarde une capture d'écran pour le débogage.
    #     """
    #     if self.driver:
    #         try:
    #             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #             filename = f"{filename_prefix}_{timestamp}.png"
    #             # S'assurer que le répertoire de screenshots existe
    #             # import os; os.makedirs("screenshots", exist_ok=True) # Si on veut un sous-dossier
    #             self.driver.save_screenshot(filename)
    #             logger.info("📸 Screenshot de débogage sauvegardé: %s", filename)
    #         except Exception as e:
    #             logger.error("❌ Impossible de sauvegarder le screenshot: %s", e)



    def save_debug_screenshot(self, filename_prefix="debug"):
        """
        📸 Sauvegarde une capture d'écran pour le débogage.
        """
        if self.driver:
            try:
                # S'assurer que le répertoire existe
                screenshots_dir = "/app/screenshots"
                if not os.path.exists(screenshots_dir):
                    os.makedirs(screenshots_dir)

                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{screenshots_dir}/{filename_prefix}_{timestamp}.png"
                
                # Sauvegarde du screenshot
                self.driver.save_screenshot(filename)
                
                # Log du HTML de la page, c'est aussi un indice précieux !
                page_source_filename = f"{screenshots_dir}/{filename_prefix}_{timestamp}.html"
                with open(page_source_filename, "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)

                logger.info("📸 Preuves sauvegardées: %s et %s", filename, page_source_filename)
                
            except Exception as e:
                logger.error("❌ Impossible de sauvegarder les preuves de débogage: %s", e)

    # --- FIN DE LA CLASSE TradingBot ---