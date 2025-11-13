# CI2D3 Ice Island Explorer - Makefile
# Convenience commands for common operations

.PHONY: help build up down restart logs clean load-data config-geoserver test

help: ## Show this help message
	@echo "CI2D3 Ice Island Explorer - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View logs from all services
	docker-compose logs -f

logs-postgis: ## View PostGIS logs
	docker-compose logs -f postgis

logs-geoserver: ## View GeoServer logs
	docker-compose logs -f geoserver

logs-api: ## View Flask API logs
	docker-compose logs -f flask-api

ps: ## Show running containers
	docker-compose ps

clean: ## Stop services and remove volumes (WARNING: deletes data)
	docker-compose down -v

load-data: ## Load shapefile into PostGIS
	docker-compose exec postgis bash /home/user/ci2d3_web/scripts/load_data.sh

load-data-python: ## Load shapefile using Python script
	docker-compose exec postgis python3 /home/user/ci2d3_web/scripts/load_data.py

config-geoserver: ## Configure GeoServer workspace and layer
	docker-compose exec geoserver bash /home/user/ci2d3_web/scripts/configure_geoserver.sh

db-shell: ## Open PostgreSQL shell
	docker-compose exec postgis psql -U geoserver -d ci2d3_db

db-count: ## Count ice island records in database
	docker-compose exec postgis psql -U geoserver -d ci2d3_db -c "SELECT COUNT(*) FROM iceislands;"

test-api: ## Test Flask API health endpoint
	curl http://localhost:5000/health

test-filter: ## Test API filter endpoint
	curl -X POST http://localhost:5000/api/filter/ -H "Content-Type: application/json" -d '{"field": "calvingloc", "operator": "=", "value": "PG"}'

test-geoserver: ## Test GeoServer WMS
	curl "http://localhost:8080/geoserver/ci2d3/wms?service=WMS&version=1.1.0&request=GetCapabilities"

install: build up load-data config-geoserver ## Complete installation (build, start, load data, configure)
	@echo ""
	@echo "Installation complete!"
	@echo "Access the application at:"
	@echo "  - Web Portal: http://localhost:8080/"
	@echo "  - GeoServer: http://localhost:8080/geoserver"
	@echo "  - Flask API: http://localhost:5000/"

status: ## Show status of all services
	@echo "=== Docker Containers ==="
	@docker-compose ps
	@echo ""
	@echo "=== Database Status ==="
	@docker-compose exec postgis psql -U geoserver -d ci2d3_db -c "SELECT COUNT(*) as ice_islands FROM iceislands;" 2>/dev/null || echo "Database not ready or no data loaded"
	@echo ""
	@echo "=== API Status ==="
	@curl -s http://localhost:5000/health || echo "API not responding"
	@echo ""
