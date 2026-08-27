# CI2D3 Ice Island Explorer

A web-based GIS portal for visualizing and exploring the Canadian Ice Island Drift,
Deterioration and Detection (CI2D3) database. It provides an interactive map with
feature inspection, attribute filtering, and lineage tracking of individual ice
islands through their fracture and drift history.

## Features

- **Interactive map viewer** — Leaflet map with a GeoServer WMS layer over ESRI World
  Imagery (default) or OpenStreetMap
- **Guided tour** — a four-step walkthrough that runs each feature live, shown on a
  visitor's first visit and re-openable from the header
- **Feature inspection** — click any ice island polygon to see all of its database fields
- **Attribute filtering** — filter by calving year, calving location, area, scene date or sensor
- **Filter layering** — stack multiple filters together with AND logic
- **Lineage tracking** — from any polygon, show its ancestors and descendants on the
  map, colour-coded by their relationship to the selected observation
- **Single public port** — the whole portal is served on port 80 behind a reverse proxy

## Architecture

| Component        | Technology                |
| ---------------- | ------------------------- |
| **Reverse proxy**| nginx 1.27 (alpine)       |
| **Frontend**     | Leaflet 1.9.4, Bootstrap 5.3.2 (vanilla JS, no build step) |
| **Backend API**  | Flask 3.0 (Python 3.11)   |
| **Database**     | PostgreSQL 16 + PostGIS   |
| **GIS Server**   | GeoServer 2.27.0 (Tomcat 9) |
| **Deployment**   | Docker Compose            |

### Request flow

Everything reaches the user through **one public port (80)**. nginx routes by path,
so the browser only ever talks to a single origin — there is no CORS involved and no
port number in any URL.

```
                    Internet
                       │
                       v
              ┌─────────────────┐
              │  nginx  :80     │   <- the ONLY publicly exposed port
              └────────┬────────┘
        ┌──────────────┼───────────────┐
        │ /            │ /geoserver/   │ /api/
        v              v               v
   ┌─────────────────────────┐   ┌──────────────┐
   │  GeoServer :8080        │   │  Flask :5000 │
   │  (also serves frontend  │   │  REST API    │
   │   from Tomcat ROOT)     │   │              │
   └───────────┬─────────────┘   └──────┬───────┘
               └───────────┬────────────┘
                           v
                 ┌────────────────────┐
                 │ PostgreSQL :5432   │
                 │   + PostGIS        │
                 └────────────────────┘

   GeoServer, Flask and PostGIS are bound to 127.0.0.1 only.
   They are not reachable from the internet.
```

## Project Structure

```
ci2d3_web/
│
├── docker/
│   ├── nginx/nginx.conf            # Reverse proxy: /, /geoserver/, /api/
│   ├── geoserver/Dockerfile        # GeoServer + Tomcat (serves the frontend)
│   ├── postgres-postgis/Dockerfile # PostgreSQL 16 + PostGIS
│   └── flask-api/Dockerfile        # Flask API
│
├── backend/
│   ├── app.py                      # Flask app factory, blueprint registration
│   ├── config.py                   # Configuration / env vars
│   ├── requirements.txt
│   ├── routes/
│   │   ├── filter_routes.py        # POST /api/filter/
│   │   ├── inspect_routes.py       # GET  /api/inspect/...
│   │   └── lineage_routes.py       # POST /api/lineage/
│   ├── services/
│   │   ├── db_service.py           # Filtering / attribute queries
│   │   ├── lineage_service.py      # Recursive lineage-tree traversal
│   │   └── geoserver_service.py    # GeoServer REST helpers
│   ├── models/iceisland_model.py
│   └── utils/
│       ├── query_builder.py        # Field-name sanitising, operator whitelist
│       └── geojson_formatter.py
│
├── frontend/
│   ├── index.html                  # Page header, filter sidebar, map, inspect panel
│   ├── js/
│   │   ├── config.js               # Resolves API/GeoServer URLs per deployment
│   │   ├── map.js                  # Map, layers, legends, lineage rendering
│   │   ├── inspect.js              # Inspect popup + Track Lineage
│   │   ├── filter.js               # Attribute metadata, filter stacking
│   │   └── tour.js                 # Guided tour shown on first visit
│   └── css/style.css
│
├── scripts/
│   ├── load_data.sh                # Load shapefile into PostGIS (+ lineage indexes)
│   ├── load_data.py
│   ├── create_lineage_indexes.sh   # Add lineage indexes to an existing database
│   └── configure_geoserver.sh      # Create workspace / datastore / layer
│
├── ref/python/                     # Reference analysis code (ci2d3.py) the lineage
│                                   # traversal was ported from. Not run by the app.
├── data/240804_ci2d3v1_epsg5937.*  # Ice island shapefile (EPSG:5937)
├── docker-compose.yml
├── AWS_DEPLOYMENT.md               # Deploying to AWS EC2
└── README.md
```

## Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 4 GB+ RAM, 10 GB+ disk

### Installation

1. **Start the stack**

   ```bash
   docker-compose up -d --build
   ```

   Four services start: `nginx` (port 80), `geoserver`, `flask-api`, `postgis`.
   Only nginx is published publicly; the rest listen on `127.0.0.1`.

2. **Wait for GeoServer** (first boot takes 2–3 minutes)

   ```bash
   docker-compose ps
   docker-compose logs -f geoserver
   ```

3. **Load the data** (also creates the lineage indexes)

   ```bash
   docker-compose exec postgis bash /scripts/load_data.sh
   ```

4. **Configure GeoServer**

   ```bash
   docker-compose exec geoserver bash /opt/scripts/configure_geoserver.sh
   ```

   Or manually at http://localhost/geoserver (`admin` / `geoserver`): create
   workspace `ci2d3`, add a PostGIS datastore (host `postgis`, port `5432`,
   database `ci2d3_db`, user `geoserver`), and publish the `iceislands` layer.

5. **Open the portal**

   | What | URL |
   | --- | --- |
   | Web portal | http://localhost/ |
   | GeoServer admin | http://localhost/geoserver |
   | API | http://localhost/api/ |
   | Health check | http://localhost/health |

For a public server, replace `localhost` with the machine's IP or domain — the
frontend detects its own origin, so no configuration change is needed.

## Usage

### Filtering

The sidebar filters observations by attribute. Each attribute offers only the
operators that make sense for it, and attributes with a fixed set of values use a
dropdown.

| Attribute | Description | Operators | Values |
| --- | --- | --- | --- |
| `calvingyr` | Year the ice island calved from its source | `=`, `!=` | 2008, 2010, 2011, 2012, NA |
| `calvingloc` | Where the ice island originated | `=`, `!=` | PG, RG, SG, CG, NG, NA |
| `area` | Area in km² | `=` `!=` `>` `<` `>=` `<=` | numeric |
| `scenedate` | Date of the satellite scene | `LIKE` | e.g. `2010-10-10` |
| `sensor` | Satellite sensor | `=`, `!=` | r1, r2, es, al |

**Why `scenedate` only offers `LIKE`:** the column is text and includes a time
component (`2010-10-10 15:34:49`), so `=` against a plain `YYYY-MM-DD` value would
never match. `LIKE` is wrapped in `%` server-side, so `2010-10-10` matches any scene
on that day.

**Stacking filters:** click **Apply Filter** for the first condition, then change the
selection and click **Additional Filter** to add another. Conditions combine with
AND, are listed under the form, and can be removed individually. **Clear Filter**
resets everything.

Example: `Calvingloc = PG` → 17,785 observations → `+ Calvingyr = 2010` → 9,658 →
`+ Area > 100` → 55.

### Guided tour

On a visitor's first visit a short tour opens automatically and *performs* each
capability against the live app rather than just describing it:

1. filter by a single attribute (`area > 200`),
2. stack a second filter (`+ calvingloc = PG`),
3. inspect an observation and show all of its database fields,
4. track that observation's lineage.

Step 4 uses an ice island whose lineage is deliberately small (40 observations), so
the demo stays cheap for the server — the whole tour makes four API calls. It is
dismissed with **Skip** or **Finish**, remembered in `localStorage`, and can be
reopened at any time with **Show me how** in the header.

### Inspecting and tracking lineage

Click any polygon to open the inspect panel (top-left of the map) showing every
database field for that observation. If the observation has an `inst` identifier,
**Track Lineage** becomes available.

Lineage is a rooted, directed tree: each observation's `lineage` field holds the
`inst` of its parent observation, linking consecutive identifications of the same ice
island across intervals with and without fracture. Clicking **Track Lineage** walks
that tree from the selected polygon and draws the result:

| Colour | Meaning |
| --- | --- |
| **Blue** | Before — ancestors, earlier observations this one came from |
| **Gold** (heavier outline) | The polygon you selected |
| **Orange** | After — descendants, later observations that came from it |
| **Grey** | Related branch (cousins; only in `all` mode) |

Polygons are numbered chronologically and joined by a dashed drift line. The button
turns into **Clear Lineage**.

## API Reference

All endpoints are served under the same origin as the portal.

### Health

```bash
curl http://localhost/health
```

### Inspect

```bash
curl http://localhost/api/inspect/123              # one feature by gid
curl http://localhost/api/inspect/attributes       # available columns + types
curl http://localhost/api/inspect/count            # total feature count
curl http://localhost/api/inspect/unique/calvingloc
```

### Filter

Single condition:

```bash
curl -X POST http://localhost/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"field": "calvingloc", "operator": "=", "value": "PG"}'
```

Multiple conditions (this is what **Additional Filter** sends):

```bash
curl -X POST http://localhost/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"filters": [
        {"field": "calvingloc", "operator": "=", "value": "PG"},
        {"field": "calvingyr",  "operator": "=", "value": "2010"},
        {"field": "area",       "operator": ">", "value": 100}
      ], "logic": "AND"}'
```

Returns a GeoJSON `FeatureCollection` (capped at 1000 features). Operators are
whitelisted and all values are bound as query parameters.

### Lineage

```bash
curl -X POST http://localhost/api/lineage/ \
  -H "Content-Type: application/json" \
  -d '{"inst": "20080718_161758_es_0_PUX", "mode": "chain"}'
```

| Mode | Returns |
| --- | --- |
| `chain` *(default)* | Ancestors **and** descendants of this observation |
| `before` | Ancestors only |
| `after` | Descendants only |
| `all` | The entire connected component (see note) |

Each feature carries a `lineage_role` of `self` / `before` / `after` / `related`, and
the response includes a `lineage` block with `total`, `truncated` and a `roles`
breakdown. Responses are capped (default 2000 features) and report the true total.

> **Note on `all`:** because every fracture descendant of a calving event ends up in
> one connected component, `all` averages ~2,800 observations and can reach ~6,300.
> `chain` averages ~290 and is what the map uses.

## Data Schema

Table `iceislands` — 25,364 observations, loaded from
`data/240804_ci2d3v1_epsg5937.shp` and reprojected from EPSG:5937 to EPSG:4326.

| Field | Type | Description |
| --- | --- | --- |
| `gid` | Integer | Primary key (generated on load) |
| `inst` | String | **Unique observation identifier** (a lineage tree vertex) |
| `lineage` | String | **The `inst` of the parent observation** (the tree edge) |
| `calvingyr` | String | Calving year |
| `calvingloc` | String | Calving location code |
| `area` | Numeric | Area (km²) |
| `perimeter` | Numeric | Perimeter (km) |
| `length` | Numeric | Maximum length (km) |
| `lon`, `lat` | Numeric | Centroid coordinates |
| `scenedate` | String | Scene date/time, `YYYY-MM-DD HH:MM:SS` |
| `imgref` | String | Source image reference |
| `sensor` | String | Sensor code |
| `beam_mode` | String | Sensor beam mode |
| `pol` | String | Polarisation |
| `mothercert`, `shpcert`, `georef`, `ddinfo` | String | Analyst certainty / provenance fields |
| `geom` | Geometry | MultiPolygon, EPSG:4326 |

Root observations have a `lineage` value that is *not* any row's `inst` (it names the
calving source, e.g. `..._P08`). There are 310 such roots; 25,304 of 25,364
observations are connected to at least one other.

> The shapefile also contains a leftover text column literally named `geometry`,
> which is unrelated to the real `geom` column. The API excludes it.

### Calving location codes

| Code | Location |
| --- | --- |
| CG | C.H. Ostenfeld Glacier |
| NA | Not Available |
| NG | North Greenland |
| PG | Petermann Glacier |
| RG | Ryder Glacier |
| SG | Steensby Glacier |

### Sensor codes

| Code | Sensor |
| --- | --- |
| r1 | Radarsat-1 |
| r2 | Radarsat-2 |
| es | Envisat |
| al | Advanced Land Imager |

## Development

### Running services individually

`docker-compose` binds GeoServer, Flask and PostGIS to `127.0.0.1`, so on the host you
can still reach them directly for debugging:

```bash
curl http://localhost:5000/health              # Flask, bypassing nginx
curl http://localhost:8080/geoserver/web/      # GeoServer, bypassing nginx
```

Opening the frontend directly on `http://localhost:8080/` also works — `config.js`
detects the port and targets `:8080` / `:5000` instead of same-origin paths.

### Frontend

Static HTML/CSS/JS with no build step. `./frontend` is bind-mounted into the Tomcat
ROOT webapp, so edits appear on refresh.

**Bump the cache-buster when you change a JS file.** The script tags in `index.html`
carry a `?v=N` query; Tomcat serves these with caching on, so without bumping `N`
browsers keep running stale JS after a redeploy.

### Backend

`./backend` is bind-mounted and `FLASK_DEBUG=1` is set, so the reloader picks up
changes. (Flask 3.x ignores `FLASK_ENV`, which is why `FLASK_DEBUG` is set explicitly —
without it, newly added routes are not registered until the container restarts.)

### Database

```bash
docker-compose exec postgis psql -U geoserver -d ci2d3_db

SELECT COUNT(*) FROM iceislands;
SELECT calvingloc, COUNT(*) FROM iceislands GROUP BY calvingloc ORDER BY 2 DESC;
```

### Lineage indexes (important)

`ogr2ogr` only creates the GIST index on `geom`. The recursive lineage query joins on
`inst` and `lineage`, so without btree indexes on those columns every step scans the
whole table — turning a ~45 ms request into one that can take minutes.

`load_data.sh` creates them automatically. For a database that was already loaded:

```bash
docker-compose exec postgis bash /scripts/create_lineage_indexes.sh
```

## Troubleshooting

**Portal not reachable on port 80**

```bash
docker-compose ps nginx
docker-compose logs nginx
```

On a cloud VM, also confirm the firewall/security group allows inbound port 80.

**Map loads but no ice islands** — the WMS layer is missing or misnamed. Check
http://localhost/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities and re-run
`configure_geoserver.sh`.

**Track Lineage returns only one polygon** — the API is running an older build without
`/api/lineage`, or the browser is running stale JS. Restart the API and hard-refresh:

```bash
docker-compose restart flask-api
```

**Lineage requests are very slow** — the lineage indexes are missing; see above.

**Changes to frontend files have no effect** — hard-refresh (Ctrl+Shift+R) and bump the
`?v=` cache-buster in `index.html`.

**Data missing**

```bash
docker-compose exec postgis psql -U geoserver -d ci2d3_db -c "SELECT COUNT(*) FROM iceislands;"
docker-compose exec postgis bash /scripts/load_data.sh
```

## Deployment

See **[AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)** for deploying to AWS EC2, including
security group configuration, HTTPS, and admin access over an SSH tunnel.

## Future Enhancements

- [ ] HTTPS by default (Let's Encrypt automation)
- [ ] Temporal filtering with a time slider
- [ ] Export functionality (GeoJSON, CSV, KML)
- [ ] OR logic in the filter UI (the API already supports it)
- [ ] User authentication for the GeoServer admin UI
- [ ] Caching and pagination for large result sets

## Acknowledgments

- CI2D3 ice island dataset and the reference analysis code in `ref/python/`
- GeoServer, PostGIS and Leaflet communities
