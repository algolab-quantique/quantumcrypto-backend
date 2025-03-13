# Utilisation de Python 3.12
FROM python:3.12-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers du projet
COPY . .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install daphne

# Définir la variable d'environnement pour Django
ENV DJANGO_SETTINGS_MODULE=quantumcrypto.settings

# Exposer le port utilisé par Daphne
EXPOSE 8000

#rassembler tous les fichiers statiques dans le répertoire défini par STATIC_ROOT
RUN python manage.py collectstatic --noinput

# Lancer Daphne pour servir l'application Django
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "quantumcrypto.asgi:application"]
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
