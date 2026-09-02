# WIRL two-server hosting (wirl.carleton.ca + geo.wirl.carleton.ca)

This directory holds everything needed to host the CI2D3 map app in its split,
two-server production shape, **without** disturbing the single-box
`docker-compose.yml` at the repo root (which stays valid for local dev / AWS).

```
Browser ──HTTPS──▶ wirl.carleton.ca/research/ice/ice-islands/ci2d3/ci2d3_v1_map/   (static app)
                        │   /geoserver/*  ──▶ https://geo.wirl.carleton.ca/geoserver/*
                        │   /api/*        ──▶ https://geo.wirl.carleton.ca/api/*
                        ▼
              ci2d3 container (nginx)  ── server-to-server, from IP 206.12.98.25
                        │                     (already on the backend allow-list)
                        ▼
        geo.wirl.carleton.ca : nginx (IP-restricted) ─▶ geoserver:8080  +  flask-api:5000 ─▶ postgis
```

**Why proxy the backend through the frontend?** The backend nginx allow-lists
only Carleton IPs (incl. `206.12.98.25` = the WordPress box). A public visitor's
browser can't reach `geo.wirl.carleton.ca` directly. Routing `/geoserver` and
`/api` through the frontend server means the backend request originates from the
allow-listed WordPress box, the browser only ever talks to one origin (so **no
CORS**), and the backend stays closed to the open internet. No change to the
backend allow-list is required.

Files:

| Path | Where it goes |
|------|---------------|
| `frontend/Dockerfile` | builds the `ci2d3-frontend` image (static app + backend proxy) |
| `frontend/ci2d3.conf` | in-container nginx config (baked into the image) |
| `frontend/ci2d3-service.snippet.yml` | one service to add to the WordPress-box compose |
| `frontend/reverse-proxy-location.snippet.conf` | two `location` blocks to add to the live reverse-proxy `default.conf` |
| `frontend/docker-compose.ci2d3.yml` | alt: run the app as its own compose project |
| `backend/docker-compose.flask.snippet.yml` | one service to add to the backend compose |
| `backend/nginx-api-location.snippet.conf` | one `location /api/` block for the backend `nginx.conf` |
| `backend/.env.example` | extra env vars for the backend `.env` |
| `backend/load_backend.sh` | loads the shapefile → PostGIS → GeoServer on the backend |

The `frontend/js/config.js` change (sub-path awareness) is already in the repo
and needs no manual edit.

---

## A. Frontend server (wirl.carleton.ca — the live WordPress box)

Only **one new container** and **one config edit**; the running site is untouched.

1. **Build the app image** (from a checkout of this repo on the box):
   ```bash
   docker build -f deploy/frontend/Dockerfile -t ci2d3-frontend:latest .
   ```

2. **Add the service.** Paste `frontend/ci2d3-service.snippet.yml` into the
   existing WordPress-box `docker-compose.yml`, and add `ci2d3` to the
   `reverse-proxy` service's `depends_on`.

3. **Add the route.** Paste the two blocks from
   `frontend/reverse-proxy-location.snippet.conf` into the **existing**
   `wirl.carleton.ca` `:443` server block in
   `reverse-proxy/nginx/conf.d/default.conf`. Nothing else in that file changes —
   the app path is a deeper prefix than `location /`, so WordPress (including the
   existing `/research/ice/ice-islands/ci2d3/` page) keeps serving everything else.

4. **Bring it up and reload the proxy:**
   ```bash
   docker compose up -d ci2d3
   docker compose exec reverse-proxy nginx -t     # validate
   docker compose exec reverse-proxy nginx -s reload
   ```

5. **Verify:** `https://wirl.carleton.ca/research/ice/ice-islands/ci2d3/ci2d3_v1_map/`
   loads the map. (The bare path without the trailing slash 301-redirects to the
   slashed form.)

To ship a frontend change later: rebuild the image and
`docker compose up -d --force-recreate ci2d3`. (Bump the `?v=` query on the
`<script>` tags in `frontend/index.html` so browsers pick up changed JS.)

---

## B. Backend server (geo.wirl.carleton.ca — PostGIS + GeoServer)

1. **Build the Flask image** (from a checkout of this repo on the box):
   ```bash
   docker build -f docker/flask-api/Dockerfile -t ci2d3-flask-api:latest .
   ```

2. **Add the service.** Paste `backend/docker-compose.flask.snippet.yml` into the
   backend `docker-compose.yml`, and add `flask-api` to the `nginx` service's
   `depends_on`. Then merge `backend/.env.example` into the backend `.env`
   (`POSTGRES_PASSWD` should already exist; add `FLASK_SECRET_KEY`).

3. **Add the API route.** Paste `backend/nginx-api-location.snippet.conf` into the
   `:443` server block in the backend `nginx.conf`, next to `location /geoserver/`.
   It reuses the same Carleton IP allow-list.

4. **Bring it up and reload nginx:**
   ```bash
   docker compose up -d flask-api
   docker compose exec nginx nginx -t
   docker compose exec nginx nginx -s reload
   ```

5. **Load the data.** Copy the shapefile (`.shp/.dbf/.shx/.prj`) into
   `/srv/geoserver/geoserver_data/ci2d3/`, then, from the backend stack directory:
   ```bash
   export POSTGRES_PASSWD=...          # same as the backend .env
   SHAPE_DIR=/srv/geoserver/geoserver_data/ci2d3 \
   SHAPEFILE_NAME=240804_ci2d3v1_epsg5937.shp \
     bash /path/to/repo/deploy/backend/load_backend.sh
   ```
   This runs the repo's `scripts/load_data.sh` (shapefile → PostGIS `geodb`,
   reprojected to EPSG:4326, with lineage indexes) and
   `scripts/configure_geoserver.sh` (workspace `ci2d3`, datastore, layer
   `iceislands`, and the calving-location SLD) against the backend containers.
   The style file is taken from the repo's `data/` directory automatically.

6. **Verify (from a Carleton IP / VPN):**
   `https://geo.wirl.carleton.ca/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities`
   lists the `iceislands` layer, and
   `https://geo.wirl.carleton.ca/api/` returns the API root JSON.

### Notes / assumptions

- The Flask container uses the built-in `flask run` server (as the repo ships).
  For a busier deployment, add `gunicorn` to `backend/requirements.txt` and change
  the service `command` to run it; not required for this low-traffic internal API.
- GeoServer's `PROXY_BASE_URL` on the backend stays `https://geo.wirl.carleton.ca/geoserver`.
  The map issues WMS/GetFeatureInfo requests with URLs it builds itself, so the
  proxy hop through `wirl.carleton.ca` needs no change there; only WMS
  *GetCapabilities* documents embed the backend host, which the app doesn't use.
- If the two servers ever share a private network, point the `proxy_pass` targets
  in `frontend/ci2d3.conf` at the internal address instead of the public host.
