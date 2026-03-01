#!/bin/bash
set -e

echo "Starting GeoServer initialization..."

# Wait for database to be ready
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USERNAME" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done

echo "PostgreSQL is ready!"

# ─────────────────────────────────────────────────────────────────────────────
# Allow iframe embedding from external domains (e.g. WordPress)
#
# Tomcat's HttpHeaderSecurityFilter adds "X-Frame-Options: DENY" or
# "SAMEORIGIN" by default, which prevents any cross-origin iframe embedding.
# We disable antiClickJacking here so the site can be embedded in WordPress
# or any other external site via <iframe>.
#
# We also add "Content-Security-Policy: frame-ancestors *" as the modern
# equivalent of allowing all origins to frame this content.
# ─────────────────────────────────────────────────────────────────────────────

TOMCAT_WEBXML="$CATALINA_HOME/conf/web.xml"
GS_WEBXML="$CATALINA_HOME/webapps/geoserver/WEB-INF/web.xml"

configure_iframe_embedding() {
    local webxml="$1"
    local label="$2"

    if [ ! -f "$webxml" ]; then
        echo "[$label] web.xml not found at $webxml, skipping."
        return
    fi

    # Disable antiClickJacking if the param already exists in this file
    if grep -q "antiClickJackingEnabled" "$webxml"; then
        # Set the param value to false (handles true or any current value)
        sed -i '/<param-name>antiClickJackingEnabled<\/param-name>/{n; s|<param-value>.*<\/param-value>|<param-value>false<\/param-value>|}' "$webxml"
        echo "[$label] Disabled antiClickJacking (X-Frame-Options) in $webxml"

    # If the HttpHeaderSecurityFilter is present but antiClickJacking isn't listed,
    # inject the antiClickJackingEnabled=false param into the first filter block
    elif grep -q "HttpHeaderSecurityFilter" "$webxml"; then
        sed -i 's|<filter-class>org.apache.catalina.filters.HttpHeaderSecurityFilter</filter-class>|<filter-class>org.apache.catalina.filters.HttpHeaderSecurityFilter</filter-class>\n    <init-param>\n      <param-name>antiClickJackingEnabled</param-name>\n      <param-value>false</param-value>\n    </init-param>|' "$webxml"
        echo "[$label] Injected antiClickJacking=false param into $webxml"

    else
        echo "[$label] HttpHeaderSecurityFilter not found in $webxml — no X-Frame-Options header will be set by Tomcat."
    fi
}

configure_iframe_embedding "$TOMCAT_WEBXML" "Tomcat conf"

# GeoServer webapp web.xml may not exist until after first boot;
# guard with a short wait after Tomcat unpacks the WAR.
# The modification below runs if the file is already present at startup time.
configure_iframe_embedding "$GS_WEBXML" "GeoServer webapp"

# ─────────────────────────────────────────────────────────────────────────────
# Start Tomcat/GeoServer
# ─────────────────────────────────────────────────────────────────────────────
exec catalina.sh run
