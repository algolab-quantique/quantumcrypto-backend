# System Install — Config Files

## Architecture Overview

The application relies on three main components to run in production:

1. **Nginx** (Web Server & Reverse Proxy)
   - Receives all internet traffic on ports 80/443.
   - Serves static files directly for performance.
   - Forwards dynamic API and WebSocket requests to Daphne.
2. **Daphne** (`bb84.service`)
   - The ASGI server running the Python/Django application code.
   - Handles the business logic and maintains persistent WebSocket connections.
3. **Redis** (`redis.service`)
   - An in-memory data store running in Docker.
   - Used by Django Channels as a message broker so different WebSocket connections (multiplayer games) can communicate with each other in real-time.

**Traffic flow:**
`User Browser <--> Nginx <--> Daphne (bb84.service) <--> Redis`

-----

# Installation Steps

## 1. Create the `quantumcrypto` user

```bash
sudo useradd -m -d /home/quantumcrypto -s /bin/bash quantumcrypto
```

## 2. Prepare the home directory and clone the repo

```bash
sudo mkdir -p /home/quantumcrypto
sudo chown quantumcrypto:quantumcrypto /home/quantumcrypto
sudo -u quantumcrypto bash -c "cd /home/quantumcrypto && git clone https://github.com/algolab-quantique/quantumcrypto-backend ."
```

## 3. Create the virtual environment and install dependencies

```bash
sudo -u quantumcrypto bash -c "cd /home/quantumcrypto && python3 -m venv ENV && source ENV/bin/activate && pip install -r requirements.txt && pip install daphne"
```

## 4. Run migrations and collect static files

```bash
sudo -u quantumcrypto bash -c "cd /home/quantumcrypto && source ENV/bin/activate && python manage.py migrate --run-syncdb"
sudo -u quantumcrypto bash -c "cd /home/quantumcrypto && source ENV/bin/activate && python manage.py collectstatic --noinput"
sudo mkdir -p /home/quantumcrypto/STATIC_FILES
sudo cp -r /home/quantumcrypto/staticfiles/* /home/quantumcrypto/STATIC_FILES/
sudo chown -R quantumcrypto:quantumcrypto /home/quantumcrypto/
```

## 5. Verify Django settings on the VM

> **Important:** `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in `settings.py` must match your public domain. Edit if needed:

```bash
grep -A1 'ALLOWED_HOSTS\|CSRF_TRUSTED' /home/quantumcrypto/quantumcrypto/settings.py
```

Example for **public domain** (`bb84.physique.usherbrooke.ca`), **not** the VM internal hostname.

You should see:

```python
ALLOWED_HOSTS = ["bb84.physique.usherbrooke.ca", "127.0.0.1", "localhost", "django"]
CSRF_TRUSTED_ORIGINS = ['https://bb84.physique.usherbrooke.ca', ...]
```

If the values are wrong, edit the file:

```bash
sudo nano /home/quantumcrypto/quantumcrypto/settings.py
```

## 6. Create the log file

```bash
sudo touch /var/quantumcrypto.log
sudo chown quantumcrypto:quantumcrypto /var/quantumcrypto.log
```

## 7. Install systemd services and nginx config

All config files are already in `/home/quantumcrypto/system_install/`. Copy them to the right locations:

```bash
# systemd services
sudo cp /home/quantumcrypto/system_install/bb84.service /etc/systemd/system/bb84.service
sudo cp /home/quantumcrypto/system_install/redis.service /etc/systemd/system/redis.service

# nginx config
sudo apt install -y nginx
sudo cp /home/quantumcrypto/system_install/quantumcrypto.nginx /etc/nginx/sites-available/quantumcrypto
sudo ln -s /etc/nginx/sites-available/quantumcrypto /etc/nginx/sites-enabled/
```


## 8. Enable and start everything

```bash
sudo systemctl daemon-reload
sudo systemctl enable bb84 redis
sudo systemctl start redis
sudo systemctl start bb84
sudo nginx -t && sudo systemctl restart nginx
```

## 9. Open the firewall

> **Warning:** Always allow port 22 before enabling ufw or you will lock yourself out!.

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw enable
```

## 10. Test the installation

```bash
# Local test
curl -H 'Host: bb84.physique.usherbrooke.ca' http://127.0.0.1

# External test (once DNS is set)
curl bb84.physique.usherbrooke.ca
```

Expected response:

```json
{"games/bb84":"http://bb84.physique.usherbrooke.ca/games/bb84/", ...}
```


## 11. Enable HTTPS with Certbot

Once the domain is live and DNS resolves correctly:

### Install Certbot and request the certificate

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d bb84.physique.usherbrooke.ca
```

When prompted:
- Enter your **email address** (used for renewal expiry alerts)
- Type `Y` to agree to the Terms of Service
- If asked about HTTP → HTTPS redirect: choose **option 2 (Redirect)** ✅

Certbot will automatically edit the nginx config to add the `listen 443 ssl` block and set up the redirect from HTTP to HTTPS.

> **Note:** If Certbot finds an existing certificate (e.g. copied from an old server), choose **option 1 (Reinstall)** to apply it to the current nginx config without wasting a renewal.

### Update Django settings

In `settings.py` on the VM, update `CSRF_TRUSTED_ORIGINS` to use `https://` — Django will reject requests otherwise:

```bash
sudo nano /home/quantumcrypto/quantumcrypto/settings.py
```

```python
CSRF_TRUSTED_ORIGINS = ['https://bb84.physique.usherbrooke.ca', ...]
```

### Restart all services

```bash
sudo systemctl restart bb84
sudo systemctl restart nginx
```

### Verify

```bash
curl https://bb84.physique.usherbrooke.ca
```

Expected response:
```json
{"games/bb84":"http://bb84.physique.usherbrooke.ca/games/bb84/", ...}
```

## 12. Updating the Code

When you pull new code from GitHub to the server, you need to apply the changes and restart the services:

```bash
# 1. Go to the project directory
cd /home/quantumcrypto

# 2. Pull the latest code
git pull origin main

# 3. Activate the Python virtual environment
source ENV/bin/activate

# 4. Apply database migrations (if any)
python manage.py migrate --run-syncdb

# 5. Collect static files (if CSS/JS changed)
python manage.py collectstatic --noinput

# 6. Restart the Daphne server to load the new Python code
sudo systemctl restart bb84
```