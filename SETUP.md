# CI2D3 Ice Island Explorer - Setup Guide

Complete step-by-step guide to set up and run the CI2D3 Ice Island Explorer.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Starting the Services](#starting-the-services)
4. [Loading Data](#loading-data)
5. [Configuring GeoServer](#configuring-geoserver)
6. [Accessing the Application](#accessing-the-application)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Docker**: Version 20.10 or higher
  - [Install Docker](https://docs.docker.com/get-docker/)
- **Docker Compose**: Version 2.0 or higher
  - [Install Docker Compose](https://docs.docker.com/compose/install/)

### System Requirements

- **RAM**: 4GB minimum, 8GB recommended
- **Disk Space**: 10GB minimum
- **CPU**: 2 cores minimum, 4 cores recommended
- **Network**: Internet connection for downloading Docker images

### Verify Installation

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Verify Docker is running
docker ps
```

---

## Initial Setup

### Step 1: Navigate to Project Directory

```bash
cd /home/user/ci2d3_web
```

### Step 2: Review Project Structure

```bash
ls -la
```

You should see:
- `docker-compose.yml`
- `backend/`
- `frontend/`
- `data/`
- `scripts/`
- `README.md`

### Step 3: Create Environment File (Optional)

```bash
cp .env.example .env
```

Edit `.env` if you want to customize settings.

---

## Starting the Services

### Step 1: Pull Docker Images

```bash
docker-compose pull
```

This downloads the required base images.

### Step 2: Build Custom Images

```bash
docker-compose build
```

This builds the GeoServer and Flask API images. **This may take 10-15 minutes** for the first build.

### Step 3: Start All Services

```bash
docker-compose up -d
```

This starts three containers:
- `ci2d3_postgis` - PostgreSQL + PostGIS database
- `ci2d3_geoserver` - GeoServer application
- `ci2d3_flask_api` - Flask REST API

### Step 4: Monitor Startup

```bash
# Watch container logs
docker-compose logs -f

# Check container status
docker-compose ps
```

Wait until you see:
- PostGIS: `database system is ready to accept connections`
- GeoServer: `Server startup in [xxxx] milliseconds`
- Flask: `Running on http://0.0.0.0:5000`

Press `Ctrl+C` to exit log view.

---

## Loading Data

### Step 1: Verify Shapefile Exists

```bash
ls -lh data/240804_ci2d3v1_epsg5937.shp
```

You should see the shapefile and its companion files (.dbf, .shx, .prj).

### Step 2: Load Data into PostGIS

**Option A: Using the Bash Script**

```bash
docker-compose exec postgis bash -c "cd / && bash /home/user/ci2d3_web/scripts/load_data.sh"
```

**Option B: Using the Python Script**

```bash
docker-compose exec postgis python3 /home/user/ci2d3_web/scripts/load_data.py
```

### Step 3: Verify Data Load

```bash
docker-compose exec postgis psql -U geoserver -d ci2d3_db -c "SELECT COUNT(*) FROM iceislands;"
```

You should see a count of ice island records.

---

## Configuring GeoServer

### Automated Configuration (Recommended)

Run the configuration script:

```bash
docker-compose exec geoserver bash /home/user/ci2d3_web/scripts/configure_geoserver.sh
```

This script will:
1. Create the `ci2d3` workspace
2. Create the PostGIS datastore
3. Publish the `iceislands` layer
4. Apply the SLD style

### Manual Configuration (Alternative)

If the automated script fails, follow these steps:

#### Step 1: Access GeoServer Admin

1. Open browser: http://localhost:8080/geoserver
2. Login with:
   - Username: `admin`
   - Password: `geoserver`

#### Step 2: Create Workspace

1. Click **Workspaces** → **Add new workspace**
2. Enter:
   - Name: `ci2d3`
   - Namespace URI: `http://ci2d3.ca`
3. Click **Save**

#### Step 3: Create PostGIS Datastore

1. Click **Stores** → **Add new Store** → **PostGIS**
2. Select workspace: `ci2d3`
3. Enter connection parameters:
   - Data Source Name: `ci2d3_postgis`
   - host: `postgis`
   - port: `5432`
   - database: `ci2d3_db`
   - user: `geoserver`
   - passwd: `geoserver123`
   - schema: `public`
4. Click **Save**

#### Step 4: Publish Layer

1. After saving the datastore, you'll see available tables
2. Click **Publish** next to `iceislands`
3. On the layer configuration page:
   - **Data** tab:
     - Set SRS to `EPSG:4326`
     - Click "Compute from data" for bounding boxes
   - **Publishing** tab:
     - Set default style (or upload the SLD from `data/ci2d3_calvingloc_sld.sld`)
4. Click **Save**

#### Step 5: Apply Custom Style (Optional)

1. Click **Styles** → **Add new style**
2. Select workspace: `ci2d3`
3. Style name: `ci2d3_calvingloc`
4. Copy content from `data/ci2d3_calvingloc_sld.sld`
5. Click **Validate** then **Save**
6. Go to **Layers** → `ci2d3:iceislands` → **Publishing** tab
7. Set Default Style to `ci2d3:ci2d3_calvingloc`
8. Click **Save**

---

## Accessing the Application

### Web Portal

The frontend can be accessed in two ways:

**Option 1: Via GeoServer (if configured)**

Copy the frontend files to the GeoServer ROOT webapp:

```bash
docker cp frontend/. ci2d3_geoserver:/usr/local/tomcat/webapps/ROOT/
```

Then access: http://localhost:8080/

**Option 2: Directly from File System**

Open `frontend/index.html` in your web browser.

**Option 3: Using a Simple HTTP Server**

```bash
cd frontend
python3 -m http.server 8000
```

Then access: http://localhost:8000/

### API Endpoints

- **API Root**: http://localhost:5000/
- **Health Check**: http://localhost:5000/health
- **Inspect**: http://localhost:5000/api/inspect/1
- **Filter**: http://localhost:5000/api/filter/

### GeoServer

- **Admin Interface**: http://localhost:8080/geoserver
- **Layer Preview**: http://localhost:8080/geoserver/web/?wicket:bookmarkablePage=:org.geoserver.web.demo.MapPreviewPage
- **WMS GetCapabilities**: http://localhost:8080/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities

---

## Verification

### 1. Check All Services are Running

```bash
docker-compose ps
```

All three services should show "Up" status.

### 2. Test Database Connection

```bash
docker-compose exec postgis psql -U geoserver -d ci2d3_db -c "\dt"
```

Should list the `iceislands` table.

### 3. Test Flask API

```bash
curl http://localhost:5000/health
```

Should return: `{"status":"healthy","service":"ci2d3-api","version":"1.0.0"}`

### 4. Test GeoServer WMS

```bash
curl "http://localhost:8080/geoserver/ci2d3/wms?service=WMS&version=1.1.0&request=GetMap&layers=ci2d3:iceislands&bbox=-180,60,-40,85&width=768&height=384&srs=EPSG:4326&format=image/png" -o test_map.png
```

Should create a PNG image file.

### 5. Test Frontend

Open the web portal and verify:
- Map loads successfully
- Ice islands are visible
- Click on an ice island shows information
- Filter panel works

---

## Troubleshooting

### Services Won't Start

**Check Docker resources:**
```bash
docker system df
docker system prune  # Clean up unused resources
```

**View detailed logs:**
```bash
docker-compose logs postgis
docker-compose logs geoserver
docker-compose logs flask-api
```

### GeoServer Takes Long to Start

GeoServer can take 2-5 minutes to fully start, especially on first run. Check logs:

```bash
docker-compose logs -f geoserver
```

Wait for: `Server startup in [xxxx] milliseconds`

### Data Loading Fails

**Check shapefile path:**
```bash
docker-compose exec postgis ls -la /data/
```

**Test PostGIS connection:**
```bash
docker-compose exec postgis psql -U geoserver -d ci2d3_db -c "SELECT PostGIS_version();"
```

**Check for GDAL/OGR:**
```bash
docker-compose exec postgis ogrinfo --version
```

### Map Doesn't Load

**Check browser console** (F12) for JavaScript errors.

**Verify configuration in frontend/js/map.js:**
- `CONFIG.geoserverUrl` matches your GeoServer URL
- `CONFIG.apiUrl` matches your Flask API URL

**Test WMS manually:**

Open in browser:
```
http://localhost:8080/geoserver/ci2d3/wms?service=WMS&request=GetCapabilities
```

### Filter Not Working

**Test API directly:**
```bash
curl -X POST http://localhost:5000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"field": "calvingloc", "operator": "=", "value": "PG"}'
```

**Check Flask logs:**
```bash
docker-compose logs flask-api
```

### CORS Errors

If seeing CORS errors in browser console:

1. Check Flask CORS configuration in `backend/config.py`
2. Verify GeoServer CORS settings in `docker-compose.yml`
3. Restart services: `docker-compose restart`

---

## Stopping and Restarting

### Stop Services

```bash
docker-compose down
```

### Stop and Remove Data

```bash
docker-compose down -v  # WARNING: This deletes the database!
```

### Restart Services

```bash
docker-compose restart
```

### Restart Single Service

```bash
docker-compose restart geoserver
```

---

## Next Steps

After successful setup:

1. **Explore the Data**: Use the filter panel to explore different ice islands
2. **Customize Styles**: Modify the SLD file and re-upload to GeoServer
3. **Add Features**: Extend the API with new endpoints
4. **Deploy to Production**: See README.md for deployment guidelines

---

## Getting Help

- Check the [README.md](README.md) for general information
- View Docker logs: `docker-compose logs -f`
- Check GeoServer logs: `docker-compose exec geoserver cat /usr/local/tomcat/logs/catalina.out`
- Review Flask logs: `docker-compose logs flask-api`

For issues, create a GitHub issue with:
- Error messages
- Docker logs
- System information
- Steps to reproduce
