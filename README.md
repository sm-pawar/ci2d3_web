# CI2D3 Ice Island Explorer

A web-based GIS portal for visualizing and exploring Canadian Ice Island datasets (CI2D3). This system provides an interactive map interface with feature inspection and attribute-based filtering capabilities.

## Features

- **Interactive Map Viewer**: Leaflet.js-based map with ice island locations
- **Feature Inspection**: Click on ice islands to view detailed attribute information
- **Dynamic Filtering**: Filter ice islands by attributes (calving location, year, area, etc.)
- **WMS/WFS Support**: GeoServer integration for efficient spatial data delivery
- **RESTful API**: Flask backend for custom queries and data access
- **Responsive Design**: Bootstrap-based UI that works on desktop and mobile

## Architecture

### Technology Stack

| Component        | Technology                |
| ---------------- | ------------------------- |
| **Frontend**     | Leaflet.js, Bootstrap 5   |
| **Backend API**  | Flask (Python 3.11)       |
| **Database**     | PostgreSQL 16 + PostGIS   |
| **GIS Server**   | GeoServer 2.27.0          |
| **Deployment**   | Docker Compose            |

### System Components

```
┌─────────────┐
│   Browser   │
│  (Leaflet)  │
└──────┬──────┘
       │
       ├──────────────┐
       │              │
       v              v
┌──────────┐   ┌──────────┐
│GeoServer │   │  Flask   │
│ WMS/WFS  │   │   API    │
└────┬─────┘   └────┬─────┘
     │              │
     └──────┬───────┘
            v
     ┌──────────────┐
     │  PostgreSQL  │
     │   + PostGIS  │
     └──────────────┘
```

## Project Structure

```
ci2d3_web/
│
├── docker/
│   ├── geoserver/
│   │   └── Dockerfile              # GeoServer image with GDAL support
│   ├── postgres-postgis/           # (uses official PostGIS image)
│   └── flask-api/
│       └── Dockerfile              # Flask API image
│
├── backend/
│   ├── app.py                      # Flask application entry point
│   ├── config.py                   # Configuration settings
│   ├── requirements.txt            # Python dependencies
│   ├── routes/
│   │   ├── filter_routes.py        # Filtering endpoints
│   │   └── inspect_routes.py       # Inspection endpoints
│   ├── services/
│   │   ├── db_service.py           # PostGIS database queries
│   │   └── geoserver_service.py    # GeoServer integration
│   ├── models/
│   │   └── iceisland_model.py      # SQLAlchemy ORM model
│   └── utils/
│       ├── query_builder.py        # Dynamic SQL query builder
│       └── geojson_formatter.py    # GeoJSON formatting utilities
│
├── frontend/
│   ├── index.html                  # Main HTML page
│   ├── js/
│   │   ├── map.js                  # Map initialization and layers
│   │   ├── inspect.js              # Feature inspection logic
│   │   └── filter.js               # Filter UI and API calls
│   └── css/
│       └── style.css               # Custom styles
│
├── scripts/
│   ├── load_data.sh                # Bash script to load shapefile
│   └── load_data.py                # Python script to load shapefile
│
├── data/
│   └── 240804_ci2d3v1_epsg5937.shp # Ice Island shapefile (EPSG:5937)
│
├── docker-compose.yml              # Docker orchestration
└── README.md                       # This file
```

## Quick Start

### Prerequisites

- Docker (20.10+)
- Docker Compose (2.0+)
- 4GB+ RAM available
- 10GB+ disk space

### Installation

1. **Clone the repository**

   ```bash
   cd ci2d3_web
   ```

2. **Start the Docker containers**

   ```bash
   docker-compose up -d
   ```

   This will start three services:
   - `postgis` - PostgreSQL + PostGIS database (port 5432)
   - `geoserver` - GeoServer (port 8080)
   - `flask-api` - Flask API (port 5000)

3. **Wait for services to be ready**

   ```bash
   # Check container status
   docker-compose ps

   # View logs
   docker-compose logs -f
   ```

4. **Load the Ice Island data into PostGIS**

   ```bash
   # Option 1: Using bash script
   docker-compose exec postgis bash /data/../scripts/load_data.sh

   # Option 2: Using Python script
   docker-compose exec postgis python3 /data/../scripts/load_data.py
   ```

5. **Configure GeoServer**

   - Open http://localhost:8080/geoserver
   - Login: `admin` / `geoserver`
   - Create workspace: `ci2d3`
   - Add PostGIS datastore:
     - Host: `postgis`
     - Port: `5432`
     - Database: `ci2d3_db`
     - User: `geoserver`
     - Password: `geoserver123`
   - Publish layer: `iceislands`

6. **Access the application**

   - Web Portal: http://localhost:8080/ (served by GeoServer)
   - Or directly: Open `frontend/index.html` in a browser
   - Flask API: http://localhost:5000/
   - GeoServer: http://localhost:8080/geoserver

## Usage

### Web Interface

1. **View Ice Islands**: The map loads with all ice islands displayed via WMS
2. **Inspect Feature**: Click on an ice island to view its attributes
3. **Filter Data**:
   - Click "Filter" in the navigation
   - Select an attribute (e.g., "Calving Location")
   - Choose an operator (e.g., "=")
   - Enter a value (e.g., "PG" for Petermann Glacier)
   - Click "Apply Filter"
4. **Clear Filter**: Click "Clear Filter" to restore all ice islands

### API Endpoints

#### Inspect Endpoints

```bash
# Get feature by ID
curl http://localhost:5000/api/inspect/123

# Get available attributes
curl http://localhost:5000/api/inspect/attributes

# Get feature count
curl http://localhost:5000/api/inspect/count

# Get unique values for a field
curl http://localhost:5000/api/inspect/unique/calvingloc
```

#### Filter Endpoint

```bash
# Filter by calving location
curl -X POST http://localhost:5000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"field": "calvingloc", "operator": "=", "value": "PG"}'

# Filter by year
curl -X POST http://localhost:5000/api/filter/ \
  -H "Content-Type: application/json" \
  -d '{"field": "carving_year", "operator": ">=", "value": 2010}'
```

## Data Schema

The Ice Island dataset includes the following attributes:

| Field            | Type    | Description                        |
| ---------------- | ------- | ---------------------------------- |
| gid              | Integer | Primary key (auto-generated)       |
| objectid         | Integer | Object identifier                  |
| iceisland_id     | String  | Unique ice island identifier       |
| calvingloc       | String  | Calving location code (CG/NA/NG/PG/RG/SG) |
| calvingdate      | Date    | Date of calving event              |
| carving_year     | Integer | Year of calving                    |
| area_km2         | Float   | Area in square kilometers          |
| perimeter_km     | Float   | Perimeter in kilometers            |
| max_length_km    | Float   | Maximum length                     |
| max_width_km     | Float   | Maximum width                      |
| thickness_m      | Float   | Ice thickness in meters            |
| source_glacier   | String  | Source glacier name                |
| geom             | Geometry| Polygon geometry (EPSG:4326)       |

### Calving Location Codes

- **CG**: Central Glacier
- **NA**: North America
- **NG**: Northern Glacier
- **PG**: Petermann Glacier
- **RG**: Ryder Glacier
- **SG**: Southern Glacier

## Development

### Backend Development

```bash
# Install dependencies
cd backend
pip install -r requirements.txt

# Run Flask development server
export FLASK_APP=app.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000
```

### Frontend Development

The frontend is static HTML/JS/CSS. Simply edit the files in `frontend/` and refresh your browser.

### Database Management

```bash
# Access PostgreSQL
docker-compose exec postgis psql -U geoserver -d ci2d3_db

# Useful queries
SELECT COUNT(*) FROM iceislands;
SELECT calvingloc, COUNT(*) FROM iceislands GROUP BY calvingloc;
SELECT * FROM iceislands WHERE carving_year >= 2010;
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory to customize settings:

```env
# Database
DB_HOST=postgis
DB_PORT=5432
DB_NAME=ci2d3_db
DB_USER=geoserver
DB_PASSWORD=geoserver123

# GeoServer
GEOSERVER_URL=http://localhost:8080/geoserver
GEOSERVER_WORKSPACE=ci2d3
GEOSERVER_LAYER=iceislands
GEOSERVER_USER=admin
GEOSERVER_PASSWORD=geoserver

# Flask
FLASK_ENV=development
SECRET_KEY=your-secret-key
```

## Troubleshooting

### Data not loading

```bash
# Check if shapefile exists
ls -lh data/240804_ci2d3v1_epsg5937.shp

# Check PostGIS connection
docker-compose exec postgis psql -U geoserver -d ci2d3_db -c '\dt'
```

### GeoServer connection issues

```bash
# Check GeoServer logs
docker-compose logs geoserver

# Restart GeoServer
docker-compose restart geoserver
```

### API errors

```bash
# Check Flask logs
docker-compose logs flask-api

# Restart Flask
docker-compose restart flask-api
```

## Future Enhancements

- [ ] Lineage tracking (parent/child ice island relationships)
- [ ] Temporal filtering with time slider
- [ ] Export functionality (GeoJSON, CSV, KML)
- [ ] User authentication and authorization
- [ ] Performance optimization and caching
- [ ] Additional visualization options (heatmaps, clustering)
- [ ] Mobile app version

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

[Add license information here]

## Contact

[Add contact information here]

## Acknowledgments

- CI2D3 Ice Island dataset
- GeoServer community
- Leaflet.js developers
- PostGIS team
