# Documentation Docker - QuantumCrypto

## Table des matières
- [1. Dockerfile](#1-dockerfile)
- [2. Docker Compose](#2-docker-compose)
  - [2.1 Services](#21-services)
    - [2.1.1 Redis](#211-redis)
    - [2.1.2 Django](#212-django)
    - [2.1.3 NGINX](#213-nginx)
  - [2.2 Réseau](#22-réseau)
- [3. Configuration NGINX](#3-configuration-nginx)
- [4. Workflow](#4-workflow-de-déploiement)
- [5. Commandes utiles](#5-commandes-utiles)
- [6. Pour la production](#6-Pour-la-production)

---

## 1. Dockerfile
Le fichier `Dockerfile` est utilisé pour créer l'image Docker de l'application Django.

```dockerfile
# Utilisation de Python 3.12
FROM python:3.12-slim
```
- Utilisation de l'image Python 3.12 (version slim pour réduire la taille)

```dockerfile
#  Définir le répertoire de travail
WORKDIR /app
```
- Crée et définit /app comme répertoire de travail pour les commandes suivantes

```dockerfile
# Copier les fichiers du projet
COPY . .
```
- Copie tous les fichiers du répertoire local courant vers /app dans le conteneur

```dockerfile
# Installer les dépendances    
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install daphne
 ```
- Installe les dépendances Python listées dans requirements.txt
- '--no-cache-dir' évite de stocker le cache pip pour réduire la taille de l''image
- Installe `daphne` un serveur ASGI pour Django **Channels**

```dockerfile
# Paramètres Django
ENV DJANGO_SETTINGS_MODULE=quantumcrypto.settings
```
- Configure le module de paramètres Django que l'application doit utiliser


```dockerfile
EXPOSE 8000
```
- Mentionne que le conteneur écoutera sur le port 8000 (pour HTTP/WebSockets)

```dockerfile
#rassembler tous les fichiers statiques dans le répertoire défini par STATIC_ROOT
RUN python manage.py collectstatic --noinput
```
- Collecte tous les fichiers statiques (CSS, JS, images) dans un seul répertoire pour la production
- '--noinput' exécute la commande sans demander de confirmation

```dockerfile
# Lancer Daphne pour servir l'application Django
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "quantumcrypto.asgi:application"]
```
- Commande par défaut exécutée lorsque le conteneur démarre
- Daphne écoute sur toutes les interfaces réseau (0.0.0.0) port 8000
- Utilise l'application ASGI définie dans quantumcrypto.asgi


---

## 2-docker-compose
Le fichier `docker-compose.yml` définit l'ensemble des **services** (Redis, Django, Nginx), réseaux et volumes nécessaires au fonctionnement de l'application. 

## 2.1 Services

## 2.1.1 Redis
```yaml
redis:
  image: redis:5
  container_name: redis
  ports:
    - "6379:6379"
  networks:
    - quantumcrypto-network
```
- Utilise l'image officielle Redis version 5
- Nomme explicitement le conteneur "redis"
- Expose le port 6379 (port par défaut de Redis) sur l'hôte
- Connecté au réseau personnalisé quantumcrypto-network
- Utilisé comme backend pour Django Channels (WebSockets) et/ou cache

## 2.1.2 Django
```yaml
django:
  build: .
  container_name: django
  command: >
    sh -c "python manage.py makemigrations &&
           python manage.py migrate --run-syncdb &&
           daphne -b 0.0.0.0 -p 8000 quantumcrypto.asgi:application"
  environment:
    - DJANGO_SETTINGS_MODULE=quantumcrypto.settings
    - SECRET_KEY=your_secret_key
    - DEBUG=True
  ports:
    - "8000:8000"
  volumes:
    - .:/app
  depends_on:
    - redis
  networks:
    - quantumcrypto-network
```
- Construit l'image à partir du Dockerfile dans le répertoire courant
- Exécute trois commandes séquentielles au démarrage:
  - makemigrations - Crée les fichiers de migration pour les modèles Django
  - migrate --run-syncdb - Applique les migrations et synchronise la base de données
  - Lance Daphne pour servir l'application ASGI
- Définit des variables d'environnement:
  - Spécifie le module de paramètres Django
  - Définit une clé secrète (à remplacer par une vraie valeur en production)
  - Active le mode debug (à désactiver en production)
- Expose le port 8000 de Daphne sur le port 8000 de l'hôte
- Monte le répertoire courant en tant que volume dans /app (développement seulement)
- Dépend du service Redis (attends que Redis soit prêt)
- Connecté au réseau personnalisé.

## 2.1.3 NGINX
```yaml
nginx:
  image: nginx:alpine
  container_name: nginx
  ports:
    - "80:80"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    - ./STATIC_FILES:/app/STATIC_FILES
  depends_on:
    - django
  networks:
    - quantumcrypto-network
```
- Utilise l'image officielle NGINX basée sur Alpine Linux (légère)
- Expose le port 80 standard HTTP
- Monte:
  - La configuration NGINX personnalisée
  - Le répertoire des fichiers statiques collectés
- Dépend du service Django
- Connecté au réseau personnalisé


## 2.2 Réseau
```yaml
networks:
  quantumcrypto-network:
    driver: bridge
```
- Crée un `réseau virtuel isolé` nommé quantumcrypto-network qui permet aux conteneurs (Django, Redis, NGINX) de communiquer entre eux de manière sécurisée.
- Les conteneurs s'appeler via leurs noms de service (django, redis, nginx) plutôt que par IP;
- Séparation physique des autres réseaux Docker sur la machine hôte;
- Bridge network : Type de réseau par défaut pour les communications inter-conteneurs.

---


## 3. Configuration NGINX
Le fichier nginx.conf configure le serveur web NGINX pour:
- Servir de reverse proxy pour Django
- Gérer les connexions WebSocket
- Servir les fichiers statiques directement

### Contenu du `nginx.conf`
```conf
events {}

http {
    server {
        listen 80;

        location / {
            proxy_pass http://django:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # Gestion des WebSockets
        location /ws/ {
            proxy_pass http://django:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Servir les fichiers statiques
        location /static/ {
           alias /app/STATIC_FILES/;
        }
    }
}
```
- proxy_pass redirige les requêtes vers le service Django

- Les en-têtes proxy_set_header préservent les informations de la requête originale

- La section /ws/ gère les connexions WebSocket avec les en-têtes appropriés

- La section /static/ sert directement les fichiers statiques depuis le volume monté
---

## 4. Workflow de déploiement

### Démarrer tous les services
```sh
docker-compose up --build -d
```

###  Vérifier les logs
```sh
docker-compose logs -f
```

### Collecte des fichiers statiques (si modification):
```sh
docker-compose exec django python manage.py collectstatic --noinput
```

### Redémarrer les conteneurs
```sh
docker-compose restart
```

### Supprimer et tout reconstruire
```sh
docker-compose down -v
docker-compose up --build -d
```

---
### 5. Commandes utiles

| Commande                                  | Description                                      |
|-------------------------------------------|--------------------------------------------------|
| `docker-compose ps`                       | Liste les conteneurs                             |
| `docker-compose up -d`                    | Lance les services en arrière-plan               |
| `docker-compose logs -f django`           | Affiche les logs en temps réel                   |
| `docker-compose exec django bash`         | Shell interactif Django                          |
| `docker-compose restart nginx`            | Redémarrage rapide de NGINX                      |
| `docker-compose down -v --remove-orphans` | Nettoyage complet avec suppression des volumes   |
| `docker system prune -a --volumes`        | Purge complète du système Docker                 |

---
## 6. Pour la production:
- Remplacez `DEBUG=True` par `DEBUG=False`
- Utilisez une vraie `SECRET_KEY`
---

##  Conclusion
Grâce à Docker, nous avons un environnement **Django + Redis + Nginx** facilement déployable. 
