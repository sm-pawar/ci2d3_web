# WIRL two-server hosting — step-by-step guide

Host the CI2D3 map app split across two servers, **without** disturbing the
single-box `docker-compose.yml` at the repo root (which stays valid for local
dev / AWS):

- **Frontend server** — `wirl.carleton.ca` (the live WordPress box, IP `206.12.98.25`).
  Serves the map app at
  `https://wirl.carleton.ca/ci2d3_v1_map/`.
- **Backend server** — `geo.wirl.carleton.ca` (existing GeoServer + nginx, IP-restricted).
  Gains a Flask API **and its own dedicated PostGIS** for the CI2D3 layer.

> **Dedicated database.** You don't have access to the existing backend PostGIS,
> so we add a **new `ci2d3-postgis` container that you own** to hold the CI2D3
> `iceislands` layer. Both the Flask API and the existing GeoServer connect to it
> over the shared `geonet` network (by container name — no host ports). The
> existing PostGIS is left completely untouched.

```
Browser ──HTTPS──▶ wirl.carleton.ca/ci2d3_v1_map/   (static app)
                        │   /geoserver/*  ──▶ https://geo.wirl.carleton.ca/geoserver/*
                        │   /api/*        ──▶ https://geo.wirl.carleton.ca/api/*
                        ▼
              ci2d3 container (nginx)  ── server-to-server, from IP 206.12.98.25
                        │                     (already on the backend allow-list)
                        ▼
        geo.wirl.carleton.ca : nginx (IP-restricted)
                        ├─▶ geoserver:8080 ──┐
                        └─▶ flask-api:5000 ──┴─▶ ci2d3-postgis:5432   (new, self-owned)
```

**Why proxy the backend through the frontend?** The backend nginx allow-lists
only Carleton IPs (incl. `206.12.98.25` = the WordPress box). A public visitor's
browser can't reach `geo.wirl.carleton.ca` directly. Routing `/geoserver` and
`/api` through the frontend server means the backend request originates from the
allow-listed WordPress box, the browser only ever talks to one origin (so **no
CORS**), and the backend stays closed to the open internet. No change to the
backend allow-list is required.

### Files in this directory

| Path | Where it goes |
|------|---------------|
| `frontend/Dockerfile` | builds the `ci2d3-frontend` image (static app + backend proxy) |
| `frontend/ci2d3.conf` | in-container nginx config (baked into the image) |
| `frontend/ci2d3-service.snippet.yml` | one service to add to the WordPress-box compose |
| `frontend/reverse-proxy-location.snippet.conf` | two `location` blocks to add to the live reverse-proxy `default.conf` |
| `frontend/docker-compose.ci2d3.yml` | alt: run the app as its own compose project |
| `backend/docker-compose.flask.snippet.yml` | two services (`ci2d3-postgis` + `flask-api`) to add to the backend compose |
| `backend/nginx-api-location.snippet.conf` | one `location /api/` block for the backend `nginx.conf` |
| `backend/.env.example` | extra env vars for the backend `.env` |
| `backend/load_backend.sh` | loads the shapefile → PostGIS → GeoServer on the backend |

The `frontend/js/config.js` change (sub-path awareness) is already in the repo
and needs no manual edit.

> **Order:** do the **backend** first (Part B) so the API and layer exist, then
> the **frontend** (Part A). Each part is self-contained; the frontend only
> starts *serving* successfully once the backend is reachable.

---

## Part B — Backend server (`geo.wirl.carleton.ca`)

Throughout, `BACKEND_STACK` is the directory that holds the existing backend
`docker-compose.yml` (the one defining `postgis`, `geoserver`, `nginx`), and
`REPO` is a checkout of this repository on the backend box. We add a new
`ci2d3-postgis` container and a `flask-api` container; the existing services are
not modified except for one added `depends_on` line on `nginx`.

### B0. Get the repo onto the box

```bash
# on geo.wirl.carleton.ca
git clone -b wirl_hosting https://github.com/sm-pawar/ci2d3_web.git ~/ci2d3_web
export REPO=~/ci2d3_web
export BACKEND_STACK=/path/to/your/backend/stack     # <-- edit: where the backend compose lives
```

### B1. Build the Flask API image

```bash
cd "$REPO"
docker build -f docker/flask-api/Dockerfile -t ci2d3-flask-api:latest .
```

### B2. Add the `ci2d3-postgis` + `flask-api` services to the backend compose

Open `$BACKEND_STACK/docker-compose.yml` and paste **both** service blocks from
`$REPO/deploy/backend/docker-compose.flask.snippet.yml` alongside the existing
services. Then add `flask-api` to the `nginx` service's `depends_on`:

```yaml
  nginx:
    depends_on:
      - geoserver
      - flask-api        # <-- add this line
```

The new `ci2d3-postgis` persists its data in a `./ci2d3_pgdata` directory next
to the compose file (created automatically on first start).

### B3. Add the secrets to the backend `.env`

Add a password for the new database and a Flask secret:

```bash
cd "$BACKEND_STACK"
{
  printf 'CI2D3_DB_PASSWORD=%s\n' "$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  printf 'FLASK_SECRET_KEY=%s\n'  "$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
} >> .env
```

(For reference, all extra vars are listed in `$REPO/deploy/backend/.env.example`.
The existing `POSTGRES_PASSWD` for the pre-existing PostGIS is left as-is.)

### B4. Add the IP-restricted `/api/` route to the backend nginx

Open the backend `nginx.conf` and paste the `location /api/ { ... }` block from
`$REPO/deploy/backend/nginx-api-location.snippet.conf` **inside** the
`listen 443 ssl;` server block for `geo.wirl.carleton.ca`, right next to the
existing `location /geoserver/`. It reuses the same Carleton allow-list.

### B5. Start the database + API and reload nginx

```bash
cd "$BACKEND_STACK"
docker compose up -d ci2d3-postgis flask-api
docker compose exec nginx nginx -t          # validate the config
docker compose exec nginx nginx -s reload   # apply the new /api/ route
```

### B6. Load the data (shapefile → `ci2d3-postgis` → GeoServer)

Copy the shapefile parts (`.shp/.dbf/.shx/.prj`) into
`/srv/geoserver/geoserver_data/ci2d3/`, then run the loader from the backend
stack directory:

```bash
cd "$BACKEND_STACK"
export CI2D3_DB_PASSWORD=...                                  # same value as the backend .env
SHAPE_DIR=/srv/geoserver/geoserver_data/ci2d3 \
SHAPEFILE_NAME=240804_ci2d3v1_epsg5937.shp \
  bash "$REPO/deploy/backend/load_backend.sh"
```

This runs the repo's `scripts/load_data.sh` (shapefile → the new `ci2d3_db`,
reprojected to EPSG:4326, with lineage indexes on `inst`/`lineage`) and
`scripts/configure_geoserver.sh` (workspace `ci2d3`, a PostGIS datastore
pointing at `ci2d3-postgis`, layer `iceislands`, and the calving-location SLD).
The style file is taken from the repo's `data/` directory automatically.

> If your GeoServer admin password isn't the default `geoserver`, add
> `GEOSERVER_ADMIN_PASSWORD=...` before `bash ...`. If the table already exists
> the script asks before dropping it — answer at the prompt.

### B7. Verify the backend (from a Carleton IP / on the VPN)

```bash
# Layer is published (should list ci2d3:iceislands):
curl -s "https://geo.wirl.carleton.ca/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities" | grep -i iceislands

# API is up (returns the API root JSON):
curl -s "https://geo.wirl.carleton.ca/api/"
```

---

## Part A — Frontend server (`wirl.carleton.ca`, the live WordPress box)

Only **one new container** and **one config edit**; the running site is
untouched. `FRONTEND_STACK` is the directory holding the WordPress
`docker-compose.yml` (the one defining `wordpress`, `mediawiki`, `erp-*`,
`reverse-proxy`), and `REPO` is a checkout of this repo on the box.

### A0. Get the repo onto the box

```bash
# on wirl.carleton.ca
git clone -b wirl_hosting https://github.com/sm-pawar/ci2d3_web.git ~/ci2d3_web
export REPO=~/ci2d3_web
export FRONTEND_STACK=/path/to/your/wordpress/stack   # <-- edit: where the WordPress compose lives
```

### A1. Build the app image (static app + backend proxy)

```bash
cd "$REPO"
docker build -f deploy/frontend/Dockerfile -t ci2d3-frontend:latest .
```

### A2. Add the `ci2d3` service to the WordPress compose

Paste the service block from `$REPO/deploy/frontend/ci2d3-service.snippet.yml`
into `$FRONTEND_STACK/docker-compose.yml`, and add `ci2d3` to the
`reverse-proxy` service's `depends_on`:

```yaml
  reverse-proxy:
    depends_on:
      - wordpress
      - mediawiki
      - erp-frontend
      - ci2d3            # <-- add this line
```

### A3. Add the route to the live reverse-proxy config

Open `$FRONTEND_STACK/reverse-proxy/nginx/conf.d/default.conf` and paste the two
blocks from `$REPO/deploy/frontend/reverse-proxy-location.snippet.conf`
**inside** the existing `wirl.carleton.ca` `:443` server block. Nothing else in
that file changes — the app path is a deeper prefix than `location /`, so
WordPress (including the existing `/research/ice/ice-islands/ci2d3/` page) keeps
serving everything else.

### A4. Start the container and reload the proxy

```bash
cd "$FRONTEND_STACK"
docker compose up -d ci2d3
docker compose exec reverse-proxy nginx -t          # validate
docker compose exec reverse-proxy nginx -s reload   # apply the new route
```

### A5. Verify

Open `https://wirl.carleton.ca/ci2d3_v1_map/` —
the map should load, tiles render, and clicking a feature / applying a filter
should work (those hit `/geoserver` and `/api`). The bare path without the
trailing slash 301-redirects to the slashed form.

```bash
# Quick smoke test from the box:
curl -sI "https://wirl.carleton.ca/ci2d3_v1_map/" | head -1
curl -s  "https://wirl.carleton.ca/ci2d3_v1_map/api/" | head -c 200
```

---

## Updating later

- **Frontend change** (HTML/CSS/JS): rebuild and recreate the container:
  ```bash
  cd "$REPO" && git pull
  docker build -f deploy/frontend/Dockerfile -t ci2d3-frontend:latest .
  cd "$FRONTEND_STACK" && docker compose up -d --force-recreate ci2d3
  ```
  Bump the `?v=` query on the `<script>` tags in `frontend/index.html` so
  browsers pick up changed JS.
- **Backend/API change**: rebuild `ci2d3-flask-api:latest` and
  `docker compose up -d --force-recreate flask-api` in `$BACKEND_STACK`.

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| Map page 502/504 | `ci2d3` container down, or reverse-proxy can't resolve it — check both are on the same `webnet`; `docker compose ps`. |
| Page loads but no tiles / API errors | Backend not reachable from the WordPress box, or the map path isn't in the backend allow-list. Confirm `206.12.98.25` is allowed for **both** `/geoserver/` and `/api/` in the backend nginx. |
| Assets 404 (broken CSS/JS) | Page opened without the trailing slash and the redirect block (A3) wasn't added — re-check `reverse-proxy-location.snippet.conf`. |
| `/api/` 403 | You're testing from a non-Carleton IP directly against `geo.wirl.carleton.ca`. That's expected — reach it via the frontend proxy, or use the VPN. |
| Loader can't find shapefile | `SHAPEFILE_NAME` doesn't match the file in `SHAPE_DIR`; pass the correct name. |

## Notes / assumptions

- The Flask container uses the built-in `flask run` server (as the repo ships).
  For a busier deployment, add `gunicorn` to `backend/requirements.txt` and change
  the service `command` to run it; not required for this low-traffic internal API.
- GeoServer's `PROXY_BASE_URL` on the backend stays `https://geo.wirl.carleton.ca/geoserver`.
  The map issues WMS/GetFeatureInfo requests with URLs it builds itself, so the
  proxy hop through `wirl.carleton.ca` needs no change there; only WMS
  *GetCapabilities* documents embed the backend host, which the app doesn't use.
- If the two servers ever share a private network, point the `proxy_pass` targets
  in `frontend/ci2d3.conf` at the internal address instead of the public host.
