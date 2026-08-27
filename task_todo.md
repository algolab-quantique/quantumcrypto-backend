# QuantumCrypto Backend — Server Incident Report & Recovery

**Date**: March 22, 2026
**Server**: `bb84.physique.usherbrooke.ca` (Proxmox VM, 40 GB disk, Ubuntu 22.04)
**Backend Path**: `/home/quantumcrypto-backend`

---

## Problem Summary

The backend was completely down. The frontend ([quantumcrypto.app](https://www.quantumcrypto.app/)) showed `Nombre de parties jouées: 0` for all protocols.

### Root Cause: Disk Full (100%)

The 40 GB disk was at **100% usage** with 0 bytes free, caused by:

| Culprit | Size | Explanation |
|---------|------|-------------|
| **`/var/cache/apparmor`** | **23 GB** | Known AppArmor cache bug on Ubuntu/Proxmox — cache grows indefinitely |
| `/var/log/journal` | 3.9 GB | Systemd journal logs with no size limits configured |
| `/var/cache/apt` | 2.2 GB | Old `.deb` package download files never cleaned |
| `/var/lib/docker` | 1.2 GB | Docker images/layers/containers accumulating |
| `/var/log/syslog` | 495 MB | System log growing without rotation |

### Cascade of Failures

```
Disk Full → Docker can't create containers → Redis crashes (March 12)
→ Django Channels (WebSockets) broken → App unusable
→ SSL cert renewal also failed (disk full) → Frontend can't reach API at all
```

---

## What We Did (Recovery Steps)

### 1. Diagnosed the Issue
```bash
sudo systemctl status bb84.service    # Running but degraded
sudo systemctl status redis.service   # FAILED since March 12 (exit code 125)
sudo systemctl status docker          # Running
df -h                                 # 100% disk usage
```

### 2. Freed Disk Space (~30 GB recovered, from 100% → 22%)
```bash
sudo rm -rf /var/cache/apparmor/*        # 23 GB freed
sudo journalctl --vacuum-size=50M        # 3.9 GB → 50 MB
sudo apt-get clean                       # 2.2 GB freed
sudo truncate -s 0 /var/log/syslog       # 495 MB freed
sudo docker system prune -a -f           # 1 GB freed
```

### 3. Fixed Docker Networking
```bash
sudo systemctl restart docker   # Rebuilt broken iptables chains
```

### 4. Fixed Redis Service File
Removed the `-d` (detach) flag from `/etc/systemd/system/redis.service`:

```diff
-ExecStart=/usr/bin/docker run --rm --name %n -p 6379:6379 -d redis:5
+ExecStart=/usr/bin/docker run --rm --name %n -p 6379:6379 redis:5
```

```bash
sudo systemctl daemon-reload
```

### 5. Restarted Services
```bash
sudo systemctl restart redis.service   # ✅ Running
sudo systemctl restart bb84.service    # ✅ Running
```

### 6. Verified Data Integrity
All game data intact in SQLite database:

| Table | BB84 | E91 | DPS | Total |
|-------|------|-----|-----|-------|
| GameStatistic | 292 | 51 | 43 | 386 |
| Game | 118 | 67 | 45 | 230 |

Database backup saved at: `/home/ibrahim/db.sqlite3.backup`

### 7. ✅ Fixed SSL Certificate
Snap certbot was broken (Proxmox VM + AppArmor = snap can't load profiles). Installed apt certbot instead:

```bash
# Installed certbot via apt (bypasses broken snap)
sudo apt install -y python3-certbot python3-certbot-nginx

# Fixed zope.interface conflict (pip version overriding apt version)
sudo pip3 uninstall zope.interface -y
sudo rm -rf /usr/local/lib/python3.10/dist-packages/zope

# Renewed certificate
sudo certbot renew   # ✅ Success!
```

**Result**: API at `https://bb84.physique.usherbrooke.ca/get_protocol_stats/` returns correct data. Frontend works on **Brave** and **Safari**. Chrome still blocked (see TODO #6).

---

## Cheat Sheet: Stop & Restart Everything

### Stop
```bash
sudo systemctl stop bb84.service
sudo systemctl stop redis.service
```

### Restart (order matters: Redis first)
```bash
sudo systemctl restart redis.service
sleep 3
sudo systemctl restart bb84.service
```

### Verify
```bash
sudo systemctl status redis.service
sudo systemctl status bb84.service
curl -I http://127.0.0.1:8008/
```

---

## ⚠️ TODO — Problems Still to Fix

### 1. 🟡 Set Up SSL Auto-Renewal
Use the apt certbot (NOT snap — snap is broken on this Proxmox VM):

```bash
sudo crontab -e
# Add: 0 3 * * * /usr/bin/certbot renew --quiet && systemctl restart nginx
```

### 2. 🟡 AppArmor Cache Bug (Prevent Recurrence)
The 23 GB cache will grow back. Set up monthly cleanup.

> [!NOTE]
> Since certbot is now installed via apt (not snap), AppArmor cache cleanup is safer.

```bash
sudo crontab -e
# Add:
0 3 1 * * rm -rf /var/cache/apparmor/* && systemctl restart apparmor
```

### 3. 🟡 Journal Log Size Limit (Prevent Recurrence)
Configure max log size to prevent journals from eating disk:

```bash
sudo nano /etc/systemd/journald.conf
# Add or uncomment: SystemMaxUse=200M
sudo systemctl restart systemd-journald
```

### 4. 🟢 Update the `system_install/` Files in Git Repo
The `.service` files in the repo (`system_install/bb84.service`, `system_install/redis.service`) are outdated — they still reference `cryptoweb` instead of `quantumcrypto`. Update them to match what's actually on the server.

### 5. 🟢 Set Up Disk Monitoring
Consider adding a simple disk space alert to avoid this happening silently again:

```bash
# Example: cron job that emails when disk > 80%
0 */6 * * * df / | awk 'NR==2{if($5+0 > 80) print "WARNING: Disk at "$5}' | mail -s "Disk Alert" admin@example.com
```

### 6. 🟡 Chrome CORS / Private Network Access Issue
The frontend works on **Brave** and **Safari**, but **NOT on Chrome**. Chrome's Private Network Access policy blocks requests from the public frontend (`quantumcrypto.app` on AWS Amplify) to the university backend (`bb84.physique.usherbrooke.ca`).

**Status**: A fix already exists in the current repo (`CORS_ALLOW_PRIVATE_NETWORK = True` in `settings.py`), but the code on the server hasn't been updated yet.

**Fix**: Merge the latest code to main, then deploy to server:
```bash
# On the server:
cd /home/quantumcrypto-backend
sudo -u cryptoweb git pull origin main
sudo -u cryptoweb ENV/bin/pip install -r requirements.txt
sudo -u cryptoweb ENV/bin/python manage.py migrate --run-syncdb
sudo systemctl restart bb84.service
```

> [!NOTE]
> The `CORS_ALLOW_PRIVATE_NETWORK = True` setting + latest `django-cors-headers` must be deployed for Chrome to work.

---

## 🐳 docker-compose is broken — Redis host mismatch (found 2026-08-27, NOT urgent)

**Status**: 🟡 OPEN — diagnosed, not fixed. Nobody uses docker-compose today (local dev and the
server install both work), so this is low priority. Recorded so it is not re-diagnosed later.

**Symptom**: bring the stack up with `docker compose up` and WebSockets/multiplayer fail.
HTTP works fine.

**Root cause** (one line): `quantumcrypto/settings.py` hardcodes the channel layer at

```python
"hosts": [('127.0.0.1', 6379)]
```

That address is correct in the two setups we actually use, and wrong in the third:

| Setup | Django runs | Redis is | `127.0.0.1` correct? |
|---|---|---|---|
| Local dev (`runserver` + `docker run redis`) | on the host | on the host (port published) | ✅ yes |
| Server (`bb84.service` + `redis.service`) | on the host (daphne native) | on the host (docker `-p 6379:6379`) | ✅ yes |
| **docker-compose** | **inside the `django` container** | separate `redis` container | ❌ **no** — `127.0.0.1` is the Django container itself |

Under docker-compose Redis is reachable at the **hostname `redis`** (the compose service name),
not at loopback.

**Fix** — make the host configurable instead of hardcoded:

```python
import os
REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1')
...
"hosts": [(REDIS_HOST, 6379)]
```

then add `- REDIS_HOST=redis` to the `django` service environment in `docker-compose.yml`.
Local dev and the server keep working unchanged (they just don't set the variable).

**Decide when picked up:** fix it as above, or delete `docker-compose.yml` + `nginx/nginx.conf`
if we do not intend to support that path — dead broken config is worse than none. Note the
docker nginx config itself is fine (`location /ws/` → `django:8000` with upgrade headers).
