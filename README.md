# Bot API Documentation

Ce projet contient le Backend et l'API du projet Bot développés avec Django Rest Framework, puis dockerisés. Ce README explique les étapes nécessaires pour configurer et déployer l'application en utilisant le Dockerfile et Docker-Compose.

## Prérequis

- **Docker**: Assurez-vous d'avoir Docker installé sur votre machine. Suivez [cette documentation](https://docs.docker.com/get-docker/) pour l'installation.
- **Docker Compose**: Docker Compose est généralement inclus avec Docker Desktop. Vous pouvez vérifier votre version avec `docker-compose --version`.

## Structure des Fichiers

- **Dockerfile** : Définit l'image Docker pour l'application Django.
- **docker-compose.yml** : Définit les services utilisés dans l'application, y compris les conteneurs PostgreSQL et Redis.
- **entrypoint.sh** : Script d'initialisation pour démarrer le serveur.
- **manage_migrations.py** : Script appelé par **entrypoint.sh** pour lancer les migrations ou les mettre à jour
- **.env** : Contient les variables d'environnement. Ce fichier n'est pas inclus dans le dépôt pour des raisons de sécurité. Assurez-vous d'en créer un avant de démarrer.

## Déploiement

1. **Cloner le dépôt**
   ```bash
   git clone <URL_DU_DEPOT>
   cd <NOM_DU_DEPOT>
   ```

2. **Construction des images**
Construire et lancer les conteneurs

Utilisez la commande suivante pour construire les images Docker (si ce n'est pas déjà fait) et lancer les conteneurs définis dans docker-compose.yml :
    ```bash
        docker-compose up --build
    ```

3. **Arrêter et nettoyer les conteneurs**
Pour arrêter les conteneurs en cours d'exécution, utilisez la commande suivante :
    ```bash
        docker-compose down
    ```
Pour supprimer les volumes créés et nettoyer toutes les données (base de données PostgreSQL), utilisez la commande suivante :
    ```bash
        docker-compose down -v
    ```

