# ==============================================================================
# CI2D3 map app - frontend container image (WordPress / wirl.carleton.ca box)
# ==============================================================================
#
# A self-contained nginx image that (1) serves the static map app and
# (2) reverse-proxies /geoserver and /api to the backend. Baking the assets in
# keeps deployment on the WordPress box independent of where the repo lives on
# disk - build the image once, then reference it from a one-line service block
# in the existing docker-compose stack.
#
#   Build context: repository root (needs ./frontend and ./deploy/frontend).
#
#   docker build -f deploy/frontend/Dockerfile -t ci2d3-frontend:latest .
#
# ==============================================================================
FROM nginx:1.27-alpine

# In-container server config (static + backend proxy).
COPY deploy/frontend/ci2d3.conf /etc/nginx/conf.d/default.conf

# Static map app -> served at the container root.
COPY frontend/ /usr/share/nginx/html/

EXPOSE 80
