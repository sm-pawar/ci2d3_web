# AWS EC2 Deployment Guide — CI2D3 Ice Island Explorer

Deploy the CI2D3 Ice Island Explorer on AWS EC2, reachable at
`http://<YOUR-EC2-PUBLIC-IP>/` with a single open web port.

## Table of Contents

1. [How the ports work](#how-the-ports-work)
2. [Prerequisites](#prerequisites)
3. [Launch the EC2 instance](#launch-the-ec2-instance)
4. [Configure the security group](#configure-the-security-group)
5. [Install dependencies](#install-dependencies)
6. [Deploy the application](#deploy-the-application)
7. [Verify the deployment](#verify-the-deployment)
8. [Admin access over an SSH tunnel](#admin-access-over-an-ssh-tunnel)
9. [Embedding the portal](#embedding-the-portal)
10. [Adding HTTPS](#adding-https)
11. [Security hardening](#security-hardening)
12. [Troubleshooting](#troubleshooting)
13. [Monitoring and backups](#monitoring-and-backups)

---

## How the ports work

The stack exposes **one public port: 80**. An nginx reverse proxy sits in front of
everything and routes by path:

| Public URL | Goes to | Purpose |
| --- | --- | --- |
| `http://<IP>/` | GeoServer Tomcat ROOT | The web portal |
| `http://<IP>/geoserver/` | GeoServer :8080 | WMS/WFS and the admin UI |
| `http://<IP>/api/` | Flask :5000 | REST API |
| `http://<IP>/health` | Flask :5000 | Health check |

GeoServer (8080), Flask (5000) and PostgreSQL (5432) are bound to `127.0.0.1` in
`docker-compose.yml`. They are reachable from the EC2 box itself and through an SSH
tunnel, **but not from the internet** — even if a security group rule were left open,
Docker is not listening on the public interface for those ports.

Because port 80 is the default for HTTP, browsers omit it. That is what makes the
site reachable at just the IP address, with no `:8080` suffix.

### A note on port 22

Port 22 is **SSH**, not a web port. The portal cannot be served there: the SSH daemon
already owns it, and moving the web server onto it would break remote administration
of the instance. It also would not improve security — an open port is an open port
regardless of its number; what matters is *how many* ports are exposed and *what*
listens on them.

The security improvement in this setup comes from reducing the public surface from
three ports (8080, 5000, and in some setups 5432) down to one (80), and keeping SSH
on 22 restricted to your own IP.

### Upgrading an existing deployment

If you previously reached the site on `:8080`, that URL **will stop working** from the
internet after this change. Update any bookmarks and — importantly — any `<iframe>`
embeds to drop the port:

```diff
- <iframe src="http://54.123.45.67:8080/" ...>
+ <iframe src="http://54.123.45.67/" ...>
```

You can then remove the 8080 and 5000 inbound rules from the security group.

---

## Prerequisites

- An AWS account with EC2 access
- Basic SSH / Linux familiarity
- A domain name (optional, required for HTTPS via Let's Encrypt)

### Minimum instance

- **Type**: `t3.medium` (2 vCPU, 4 GB RAM) or larger
- **Storage**: 20 GB gp3 minimum, 50 GB recommended
- **OS**: Ubuntu 22.04 LTS or newer

---

## Launch the EC2 instance

1. EC2 Console → **Launch Instance**
2. Configure:
   - **Name**: `ci2d3-ice-island-explorer`
   - **AMI**: Ubuntu Server 22.04 LTS
   - **Instance type**: `t3.medium`
   - **Key pair**: create or select an SSH key pair
   - **Storage**: 20 GB gp3
3. Launch, wait for **Running**, and note the **public IPv4 address**
   (e.g. `54.123.45.67`).

Consider attaching an **Elastic IP** so the address survives a stop/start.

Connect:

```bash
ssh -i "your-key.pem" ubuntu@54.123.45.67
```

---

## Configure the security group

Only two inbound rules are needed.

| Type | Protocol | Port | Source | Purpose |
| --- | --- | --- | --- | --- |
| SSH | TCP | 22 | **My IP** | Administration |
| HTTP | TCP | 80 | `0.0.0.0/0` | The portal |
| HTTPS | TCP | 443 | `0.0.0.0/0` | Only if you add TLS |

**Do not open 8080, 5000 or 5432.** Those services listen on loopback only, so such
rules would grant nothing — but leaving them in place is misleading and risky if the
binding is ever changed back.

In the console: EC2 → your instance → **Security** tab → security group →
**Edit inbound rules** → keep only the rows above → **Save rules**.

Restricting SSH to *My IP* rather than `0.0.0.0/0` is the single highest-value change
here — it removes the instance from the constant background of SSH brute-force scans.

---

## Install dependencies

```bash
sudo apt update && sudo apt upgrade -y

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Docker Compose plugin + git
sudo apt install -y docker-compose-v2 git

docker --version
docker compose version
```

Log out and back in so the `docker` group membership applies:

```bash
exit
ssh -i "your-key.pem" ubuntu@54.123.45.67
```

> This guide writes `docker-compose`. On newer installs the command is
> `docker compose` (a space). Both work the same way.

---

## Deploy the application

### 1. Clone the repository

```bash
git clone https://github.com/sm-pawar/ci2d3_web.git
cd ci2d3_web
```

### 2. Set your own passwords

The defaults in `docker-compose.yml` are development credentials. Change them before
exposing the instance:

- `POSTGRES_PASSWORD` / `DB_PASSWORD` (must match across `postgis` and `flask-api`)
- `GEOSERVER_ADMIN_PASSWORD`

### 3. Build and start

```bash
docker-compose up -d --build
```

The GeoServer image takes 10–15 minutes to build the first time.

```bash
docker-compose ps
docker-compose logs -f
```

Look for:
- postgis: `database system is ready to accept connections`
- geoserver: `Server startup in [xxxx] milliseconds`
- flask-api: `Running on http://0.0.0.0:5000`
- nginx: no errors

### 4. Load the ice island data

```bash
docker-compose exec postgis bash /scripts/load_data.sh
```

This loads the shapefile, reprojects it to EPSG:4326, and creates the btree indexes
on `inst` and `lineage` that the lineage traversal needs.

Verify:

```bash
docker-compose exec postgis psql -U geoserver -d ci2d3_db \
  -c "SELECT COUNT(*) FROM iceislands;"     # expect 25364
```

### 5. Configure GeoServer

```bash
docker-compose exec geoserver bash /opt/scripts/configure_geoserver.sh
```

This creates the `ci2d3` workspace, the PostGIS datastore and the `iceislands` layer.

---

## Verify the deployment

From your own machine:

```bash
# Portal
curl -I http://54.123.45.67/

# API health
curl http://54.123.45.67/health

# Attributes
curl http://54.123.45.67/api/inspect/attributes

# Combined filter
curl -X POST http://54.123.45.67/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"filters":[{"field":"calvingloc","operator":"=","value":"PG"},
                  {"field":"calvingyr","operator":"=","value":"2010"}],
       "logic":"AND"}'

# Lineage
curl -X POST http://54.123.45.67/api/lineage/ \
  -H "Content-Type: application/json" \
  -d '{"inst":"20080718_161758_es_0_PUX","mode":"chain"}'

# WMS capabilities
curl "http://54.123.45.67/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities" | head
```

Confirm the internal ports are **not** publicly reachable (these should fail):

```bash
curl --max-time 5 http://54.123.45.67:8080/   # expect timeout / refused
curl --max-time 5 http://54.123.45.67:5000/   # expect timeout / refused
```

Then open `http://54.123.45.67/` in a browser and check:

- the map and basemap load
- ice island polygons are drawn
- clicking a polygon opens the inspect panel on the left
- **Track Lineage** draws the before/after coloured lineage
- **Apply Filter** and **Additional Filter** both narrow the result

---

## Admin access over an SSH tunnel

Because 8080 and 5000 are no longer public, reach them by forwarding through SSH:

```bash
ssh -i "your-key.pem" -L 8080:localhost:8080 -L 5000:localhost:5000 \
    ubuntu@54.123.45.67
```

While that session is open, on your own machine:

- GeoServer admin → http://localhost:8080/geoserver
- Flask API → http://localhost:5000/health

For the database:

```bash
ssh -i "your-key.pem" -L 5432:localhost:5432 ubuntu@54.123.45.67
psql -h localhost -U geoserver -d ci2d3_db
```

The GeoServer admin UI is also reachable publicly at `http://<IP>/geoserver/web/`. If
you would rather it were not, uncomment the IP-restriction block in
`docker/nginx/nginx.conf` and set your address — WMS/WFS keeps working for everyone.

---

## Embedding the portal

```html
<iframe src="http://54.123.45.67/"
        width="100%" height="625"
        style="border:none; display:block;"
        title="CI2D3 Ice Island Explorer"
        loading="lazy"></iframe>
```

nginx removes `X-Frame-Options` and sets `Content-Security-Policy: frame-ancestors *`,
so the portal can be framed by another site.

**If the host page is HTTPS**, browsers silently block an `http://` iframe as mixed
content. This is the most common reason an embed shows a blank box — add TLS (below)
and embed via `https://`.

Some WordPress installs strip `<iframe>` from post content. If the tag disappears on
save, add it through a Custom HTML block, and if that still fails allow the tag in
your theme's `wp_kses_allowed_html` filter.

---

## Adding HTTPS

Let's Encrypt requires a **domain name** — it will not issue certificates for bare IP
addresses. Point a domain at the instance first (Route 53 or any DNS provider):

```
iceislands.example.org  A  54.123.45.67
```

Then, on the instance:

```bash
sudo apt install -y certbot
docker-compose stop nginx           # free port 80 for the challenge
sudo certbot certonly --standalone -d iceislands.example.org
```

Mount the certificates into the nginx container by adding to the `nginx` service in
`docker-compose.yml`:

```yaml
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    ports:
      - "80:80"
      - "443:443"
```

Then add a TLS server block to `docker/nginx/nginx.conf`, redirecting HTTP to HTTPS:

```nginx
    server {
        listen 80;
        server_name iceislands.example.org;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl;
        server_name iceislands.example.org;

        ssl_certificate     /etc/letsencrypt/live/iceislands.example.org/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/iceislands.example.org/privkey.pem;

        # ... same proxy_set_header lines and location blocks as the port 80 server
    }
```

Restart and add renewal:

```bash
docker-compose up -d nginx
echo "0 3 * * * root certbot renew --quiet --pre-hook 'docker-compose -f /home/ubuntu/ci2d3_web/docker-compose.yml stop nginx' --post-hook 'docker-compose -f /home/ubuntu/ci2d3_web/docker-compose.yml start nginx'" | sudo tee /etc/cron.d/certbot-renew
```

The frontend needs no change — `config.js` uses whatever origin the page was served
from, so it follows automatically to `https://`.

---

## Security hardening

1. **Change the default passwords** (database and GeoServer admin) before going
   public. The database password appears in both the `postgis` and `flask-api`
   service definitions and must match.

2. **Restrict SSH to your own IP** in the security group.

3. **Keep only ports 22, 80 (and 443) open.** Everything else stays on loopback.

4. **Restrict the GeoServer admin UI** — uncomment the IP allow-list in
   `docker/nginx/nginx.conf` if you do not need it publicly reachable.

5. **Turn off Flask debug mode for production.** `docker-compose.yml` sets
   `FLASK_DEBUG: 1` for development convenience; the debugger must not be exposed on
   a public server. Set it to `0` and use a WSGI server such as gunicorn instead of
   `flask run`.

6. **Tighten CORS.** `CORS_ALLOWED_ORIGINS` is `*`. With the reverse proxy the
   frontend is same-origin and no longer needs CORS at all, so this can be narrowed to
   the sites that embed the portal.

7. **Keep the host patched.**

   ```bash
   sudo apt update && sudo apt upgrade -y
   docker-compose pull && docker-compose up -d
   ```

---

## Troubleshooting

### The site does not load on port 80

```bash
docker-compose ps nginx
docker-compose logs nginx
sudo ss -tulpn | grep ':80'
```

Then confirm the security group has an inbound rule for port 80 from `0.0.0.0/0`.

### nginx starts but returns 502 Bad Gateway

nginx is up but a backend is not. Check which:

```bash
docker-compose ps
curl http://localhost:8080/geoserver/web/   # on the EC2 box
curl http://localhost:5000/health
```

GeoServer takes 2–3 minutes to start; 502s during that window are expected.

### Map loads but no ice islands appear

```bash
curl "http://localhost/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities" | head
docker-compose exec geoserver bash /opt/scripts/configure_geoserver.sh
```

### Track Lineage shows only one polygon

The API is running an older build, or the browser cached old JavaScript:

```bash
docker-compose restart flask-api
curl http://localhost/api/lineage/ -X POST -H 'Content-Type: application/json' \
  -d '{"inst":"20080718_161758_es_0_PUX","mode":"chain"}' | head -c 300
```

Then hard-refresh the browser (Ctrl+Shift+R).

### Lineage requests take minutes

The lineage indexes are missing:

```bash
docker-compose exec postgis bash /scripts/create_lineage_indexes.sh
```

### Frontend edits have no effect

`./frontend` is bind-mounted, so files update live — but browsers cache the JS. Bump
the `?v=N` cache-buster on the script tags in `frontend/index.html` and hard-refresh.

### Checking what is actually exposed

```bash
# On the EC2 box: 0.0.0.0:80 should be the only public listener
sudo ss -tulpn | grep docker
```

---

## Monitoring and backups

### Health

```bash
docker-compose ps
docker stats --no-stream
df -h
```

A minimal check script:

```bash
#!/bin/bash
curl -sf http://localhost/            > /dev/null && echo "✓ portal"    || echo "✗ portal"
curl -sf http://localhost/health      > /dev/null && echo "✓ api"       || echo "✗ api"
curl -sf http://localhost/geoserver/web/ > /dev/null && echo "✓ geoserver" || echo "✗ geoserver"
docker-compose exec -T postgis psql -U geoserver -d ci2d3_db -c '\q' 2>/dev/null \
  && echo "✓ postgis" || echo "✗ postgis"
```

### Logs

```bash
docker-compose logs --tail=100 -f
docker-compose logs -f nginx        # includes all public request traffic
```

### Backups

```bash
# Database
docker-compose exec -T postgis pg_dump -U geoserver ci2d3_db > backup_$(date +%Y%m%d).sql

# GeoServer configuration
docker-compose exec geoserver tar czf /tmp/gs_backup.tar.gz /opt/geoserver_data
docker cp ci2d3_geoserver:/tmp/gs_backup.tar.gz ./
```

---

## Cost reference (us-east-1, on-demand)

| Instance type | Approx. monthly | Use case |
| --- | --- | --- |
| t3.medium | ~$30 | Development / light use |
| t3.large | ~$60 | Small production |
| t3.xlarge | ~$121 | Medium production |

Reserved Instances or Savings Plans cut this substantially for long-running
deployments. Stop the instance when idle, and use an Elastic IP so the address is
preserved across stop/start.

---

## Summary

```
Portal            http://YOUR_EC2_PUBLIC_IP/
GeoServer admin   http://YOUR_EC2_PUBLIC_IP/geoserver
API               http://YOUR_EC2_PUBLIC_IP/api/
Health            http://YOUR_EC2_PUBLIC_IP/health

Public ports      22 (SSH, your IP only) and 80
Internal only     8080 GeoServer, 5000 Flask, 5432 PostgreSQL (127.0.0.1)
```
