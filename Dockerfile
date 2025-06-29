# # Utilise une image Python officielle. Python 3.10+ est requis pour Django 5.x
# FROM python:3.10-slim-bullseye 

# # Définit les variables d'environnement
# ENV PYTHONDONTWRITEBYTECODE 1
# ENV PYTHONUNBUFFERED 1

# # Répertoire de travail
# WORKDIR /app

# # Installer les dépendances système de base
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     # ... (liste des dépendances système comme avant) ...
#     wget \
#     gnupg \
#     unzip \
#     ca-certificates \
#     libglib2.0-0 \
#     libnss3 \
#     libgconf-2-4 \
#     libfontconfig1 \
#     libx11-6 \
#     libx11-xcb1 \
#     libxcb1 \
#     libxcomposite1 \
#     libxcursor1 \
#     libxdamage1 \
#     libxext6 \
#     libxfixes3 \
#     libxi6 \
#     libxrandr2 \
#     libxrender1 \
#     libxss1 \
#     libxtst6 \
#     libasound2 \
#     libatk1.0-0 \
#     libatk-bridge2.0-0 \
#     libcups2 \
#     libdrm2 \
#     libgbm1 \
#     libgtk-3-0 \
#     libxshmfence1 \
#     && rm -rf /var/lib/apt/lists/*

# # Définir la version de Chrome for Testing et ChromeDriver (elles DOIVENT correspondre)
# # Vérifie la dernière version stable compatible avec Python 3.10+
# # Exemple avec une version plus récente de Chrome pour aller avec Python 3.10+
# ARG CHROME_VERSION_FULL=122.0.6261.94 
#                                      # Vérifie sur https://googlechromelabs.github.io/chrome-for-testing/

# # Installer Chrome for Testing
# RUN CHROME_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION_FULL}/linux64/chrome-linux64.zip" && \
#     echo "Downloading Chrome for Testing ${CHROME_VERSION_FULL} from ${CHROME_URL}" && \
#     wget -q -P /tmp "${CHROME_URL}" -O /tmp/chrome-linux64.zip && \
#     mkdir -p /opt/chrome-for-testing && \
#     unzip -q /tmp/chrome-linux64.zip -d /opt/chrome_temp && \
#     mv /opt/chrome_temp/chrome-linux64/* /opt/chrome-for-testing/ && \
#     ln -sf /opt/chrome-for-testing/chrome /usr/local/bin/google-chrome && \
#     ln -sf /opt/chrome-for-testing/chrome /usr/local/bin/chrome && \
#     rm /tmp/chrome-linux64.zip && \
#     rm -rf /opt/chrome_temp && \
#     echo "Vérification de Chrome après installation:" && \
#     google-chrome --version 

# # Installer ChromeDriver correspondant
# RUN CHROMEDRIVER_URL="https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing/${CHROME_VERSION_FULL}/linux64/chromedriver-linux64.zip" && \
#     echo "Downloading ChromeDriver ${CHROME_VERSION_FULL} from ${CHROMEDRIVER_URL}" && \
#     wget -q -P /tmp "${CHROMEDRIVER_URL}" -O /tmp/chromedriver.zip && \
#     mkdir -p /opt/chromedriver && \
#     unzip -q /tmp/chromedriver.zip -d /opt/chromedriver_temp && \
#     mv /opt/chromedriver_temp/chromedriver-linux64/chromedriver /opt/chromedriver/chromedriver && \
#     (mv /opt/chromedriver_temp/chromedriver-linux64/LICENSE.chromedriver /opt/chromedriver/LICENSE.chromedriver || echo "Pas de LICENSE.chromedriver trouvé, continuant...") && \
#     chmod +x /opt/chromedriver/chromedriver && \
#     ln -sf /opt/chromedriver/chromedriver /usr/local/bin/chromedriver && \
#     rm /tmp/chromedriver.zip && \
#     rm -rf /opt/chromedriver_temp && \
#     echo "Vérification de ChromeDriver après installation:" && \
#     chromedriver --version

# # Copier les requirements et les installer
# COPY ./requirements.txt /app/requirements.txt
# # Mettre à jour pip avant d'installer les requirements peut aider avec les nouvelles versions de Python
# RUN pip install --upgrade pip
# RUN pip install --no-cache-dir -r requirements.txt

# # Copier le reste du projet
# COPY . /app/

# # Exposer le port
# EXPOSE 8000

# # CMD sera dans docker-compose



FROM python:3.11.7-slim

RUN apt-get update \
&& apt-get install -y wget gpg
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome-keyring.gpg \
&& echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
&& apt-get update \
&& apt-get install -y google-chrome-stable

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# RUN apt-get update && apt-get install -y netcat dos2unix
RUN apt-get update && apt-get install -y netcat-traditional dos2unix
RUN pip install --upgrade pip

COPY requirements.txt .
ENV PIP_ROOT_USER_ACTION=ignore
RUN pip install --no-cache-dir -r requirements.txt

COPY entrypoint.sh .
RUN dos2unix entrypoint.sh
RUN sed -i 's/\r$//g' entrypoint.sh
RUN chmod +x entrypoint.sh

COPY . .
COPY Trading_cookies.json ./Trading_cookies.json

EXPOSE 8000

CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
ENTRYPOINT ["sh", "/app/entrypoint.sh"]