/**
 * CI2D3 Ice Island Explorer - Map Module
 * Handles Leaflet map initialization and layer management
 */

// Configuration is loaded from config.js
// CONFIG variable is available globally

// Global variables
let map;
let wmsLayer;
let filteredLayer;
let lineageLayer;
let lineageLegend;
let currentFilteredData = null;
let currentLineageData = null;

/**
 * Initialize the Leaflet map
 */
function initMap() {
    // Create map centered on Canadian Arctic
    map = L.map('map', {
        center: [75.0, -90.0],
        zoom: 4,
        minZoom: 2,
        maxZoom: 18
    });

    // Create custom panes for proper layer ordering
    // Basemap pane with lower z-index
    map.createPane('basemapPane');
    const basemapPane = map.getPane('basemapPane');
    basemapPane.style.zIndex = 100; // Lower than default tilePane (200)
    basemapPane.classList.add('custom-basemap-pane'); // Add custom class for CSS

    // WMS overlay pane with MUCH higher z-index to ensure it's on top
    map.createPane('wmsPane');
    const wmsOverlayPane = map.getPane('wmsPane');
    wmsOverlayPane.style.zIndex = 900; // Much higher than all default panes
    wmsOverlayPane.classList.add('custom-wms-pane'); // Add custom class for CSS

    console.log('Basemap pane z-index:', basemapPane.style.zIndex);
    console.log('WMS pane z-index:', wmsOverlayPane.style.zIndex);

    // Add base map layers - assign to basemapPane
    const baseLayers = {
        'ESRI World Imagery': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
            maxZoom: 18,
            pane: 'basemapPane'
        }),
        'OpenStreetMap': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19,
            pane: 'basemapPane'
        })
    };

    // Add default base layer
    baseLayers['ESRI World Imagery'].addTo(map);

    // Create WMS layer (but don't add yet)
    const wmsUrl = `${CONFIG.geoserverUrl}/wms`;
    const layerName = `${CONFIG.workspace}:${CONFIG.layer}`;

    wmsLayer = L.tileLayer.wms(wmsUrl, {
        layers: layerName,
        format: 'image/png',
        transparent: true,
        version: '1.1.0',
        attribution: 'CI2D3 Ice Island Data',
        opacity: 0.7,
        maxZoom: 18,
        pane: 'wmsPane' // Use custom high z-index pane (900) to ensure layer appears on top
    });

    // Add WMS layer to map immediately to ensure it's visible
    wmsLayer.addTo(map);

    // Create overlay layers object for layer control
    const overlayLayers = {
        'Static CI2D3 Database Layer': wmsLayer
    };

    // Add layer control with overlays
    const layerControl = L.control.layers(baseLayers, overlayLayers, {
        position: 'topright',
        collapsed: false
    }).addTo(map);

    // Ensure WMS layer stays on top when basemap is changed
    map.on('baselayerchange', function() {
        if (wmsLayer && wmsLayer._map) {
            wmsLayer.bringToFront();
        }
    });

    // Add click handler for WMS GetFeatureInfo
    map.on('click', function(e) {
        if (wmsLayer._map) {
            getFeatureInfo(e.latlng);
        }
    });

    // Add scale
    L.control.scale({ imperial: false, position: 'bottomleft' }).addTo(map);

    // Add legend
    addLegend();

    // Force WMS layer to front after a short delay to ensure it's on top
    setTimeout(() => {
        if (wmsLayer && wmsLayer._map) {
            wmsLayer.bringToFront();
            console.log('WMS layer brought to front');
        }
    }, 500);

    console.log('Map initialized successfully');
}

/**
 * Get feature info from WMS layer on click
 */
function getFeatureInfo(latlng) {
    const point = map.latLngToContainerPoint(latlng);
    const size = map.getSize();
    const params = {
        request: 'GetFeatureInfo',
        service: 'WMS',
        srs: 'EPSG:4326',
        version: '1.1.0',
        format: 'image/png',
        bbox: map.getBounds().toBBoxString(),
        height: size.y,
        width: size.x,
        layers: `${CONFIG.workspace}:${CONFIG.layer}`,
        query_layers: `${CONFIG.workspace}:${CONFIG.layer}`,
        info_format: 'application/json',
        x: Math.round(point.x),
        y: Math.round(point.y)
    };

    const url = `${CONFIG.geoserverUrl}/ci2d3/wms?${new URLSearchParams(params)}`;

    showLoading(true);

    fetch(url)
        .then(response => response.json())
        .then(data => {
            if (data.features && data.features.length > 0) {
                const feature = data.features[0];
                displayFeatureInfo(feature);
            }
        })
        .catch(error => {
            console.error('Error getting feature info:', error);
        })
        .finally(() => {
            showLoading(false);
        });
}

/**
 * Add filtered GeoJSON layer to map
 */
function addFilteredLayer(geojson) {
    // Remove existing filtered layer
    if (filteredLayer) {
        map.removeLayer(filteredLayer);
    }

    // Store filtered data
    currentFilteredData = geojson;

    // Create GeoJSON layer
    filteredLayer = L.geoJSON(geojson, {
        style: function(feature) {
            return {
                color: getColorForCalvingLoc(feature.properties.calvingloc),
                weight: 2,
                opacity: 0.8,
                fillOpacity: 0.5
            };
        },
        onEachFeature: function(feature, layer) {
            layer.on('click', function() {
                displayFeatureInfo(feature);
            });
        }
    });

    filteredLayer.addTo(map);

    // Zoom to filtered features
    if (filteredLayer.getBounds().isValid()) {
        map.fitBounds(filteredLayer.getBounds(), { padding: [50, 50] });
    }

    // Hide WMS layer when showing filtered layer
    if (wmsLayer && wmsLayer._map) {
        map.removeLayer(wmsLayer);
    }
}

/**
 * Clear filtered layer and restore WMS
 */
function clearFilteredLayer() {
    if (filteredLayer) {
        map.removeLayer(filteredLayer);
        filteredLayer = null;
        currentFilteredData = null;
    }

    // Clear lineage layer as well
    clearLineageLayer();

    // // Restore WMS layer
    // if (wmsLayer && !wmsLayer._map) {
    //     wmsLayer.addTo(map);
    // }
}

/**
 * Colour scheme for lineage features
 */
const LINEAGE_ROLE_STYLES = {
    before: {
        fill: '#1f78b4', border: '#0f4c81',
        weight: 2, fillOpacity: 0.45,
        label: 'Before (ancestor)'
    },
    after: {
        fill: '#e6550d', border: '#a63603',
        weight: 2, fillOpacity: 0.45,
        label: 'After (descendant)'
    },
    self: {
        fill: '#ffd400', border: '#7a5c00',
        weight: 4, fillOpacity: 0.75,
        label: 'Selected polygon'
    },
    related: {
        fill: '#9e9e9e', border: '#616161',
        weight: 2, fillOpacity: 0.35,
        label: 'Related branch'
    }
};

/**
 * Add lineage layer to map with special styling
 */
function addLineageLayer(geojson, lineageValue) {
    // Remove existing lineage layer
    clearLineageLayer();

    // Remove existing filtered layer
    if (filteredLayer) {
        map.removeLayer(filteredLayer);
        filteredLayer = null;
    }

    // Store lineage data
    currentLineageData = geojson;

    // Sort features by scene date to establish order (if available)
    const sortedFeatures = [...geojson.features].sort((a, b) => {
        const dateA = a.properties.scenedate || a.properties.scene_date || '';
        const dateB = b.properties.scenedate || b.properties.scene_date || '';
        return dateA.localeCompare(dateB);
    });

    // Create the lineage layer group
    lineageLayer = L.layerGroup();

    // Numbered markers are only useful (and only performant) for modestly
    // sized lineages. Large lineages still render their polygons and the
    // drift connector line.
    const MAX_LINEAGE_MARKERS = 250;
    const showMarkers = sortedFeatures.length <= MAX_LINEAGE_MARKERS;
    if (!showMarkers) {
        console.log(
            `Lineage has ${sortedFeatures.length} features; ` +
            `skipping numbered markers (limit ${MAX_LINEAGE_MARKERS}).`
        );
    }

    // Add connection lines between consecutive features (parent-child links)
    if (sortedFeatures.length > 1) {
        const lineCoords = [];
        sortedFeatures.forEach(feature => {
            const centroid = getFeatureCentroid(feature);
            if (centroid) {
                lineCoords.push([centroid[1], centroid[0]]); // [lat, lng]
            }
        });

        if (lineCoords.length > 1) {
            const connectionLine = L.polyline(lineCoords, {
                color: '#ff6b35',
                weight: 3,
                opacity: 0.8,
                dashArray: '10, 5',
                className: 'lineage-connection'
            });
            lineageLayer.addLayer(connectionLine);
        }
    }

    // Add polygon features with numbered markers
    sortedFeatures.forEach((feature, index) => {
        // Colour by the feature's relationship to the clicked polygon, as
        // tagged by the API (self / before / after / related).
        const role = feature.properties.lineage_role || 'related';
        const style = LINEAGE_ROLE_STYLES[role] || LINEAGE_ROLE_STYLES.related;

        // Create polygon layer
        const polygonLayer = L.geoJSON(feature, {
            style: {
                color: style.border,
                weight: style.weight,
                opacity: 1,
                fillColor: style.fill,
                fillOpacity: style.fillOpacity
            },
            onEachFeature: function(f, layer) {
                layer.on('click', function() {
                    displayFeatureInfo(f);
                });

                // Tooltip: sequence number, relationship, and date
                const tooltip =
                    `#${index + 1} &middot; ${style.label}<br>` +
                    `${f.properties.scenedate || 'Unknown date'}`;
                layer.bindTooltip(tooltip, {
                    permanent: false,
                    direction: 'top',
                    className: 'lineage-tooltip'
                });
            }
        });

        lineageLayer.addLayer(polygonLayer);

        // Add numbered marker at centroid.
        // Skipped for large lineages: thousands of DivIcon markers stall the
        // browser and the numbers become unreadable at that density anyway.
        const centroid = showMarkers ? getFeatureCentroid(feature) : null;
        if (centroid) {
            const marker = L.marker([centroid[1], centroid[0]], {
                icon: L.divIcon({
                    className: 'lineage-marker',
                    html: `<div class="lineage-number" style="background-color: ${style.border}">${index + 1}</div>`,
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                })
            });
            lineageLayer.addLayer(marker);
        }
    });

    // Add layer to map
    lineageLayer.addTo(map);

    // Show a legend explaining the before/after colours
    addLineageLegend(geojson.lineage || {});

    // Zoom to lineage features
    const allPolygons = L.geoJSON(geojson);
    if (allPolygons.getBounds().isValid()) {
        map.fitBounds(allPolygons.getBounds(), { padding: [50, 50] });
    }

    // Hide WMS layer when showing lineage layer
    if (wmsLayer && wmsLayer._map) {
        map.removeLayer(wmsLayer);
    }

    console.log(`Lineage layer added with ${geojson.features.length} features for lineage: ${lineageValue}`);
}

/**
 * Add a legend describing the lineage colour scheme.
 */
function addLineageLegend(meta) {
    removeLineageLegend();

    const counts = meta.roles || {};

    lineageLegend = L.control({ position: 'topright' });
    lineageLegend.onAdd = function() {
        const div = L.DomUtil.create('div', 'legend lineage-legend-box');
        let html = '<h6><strong>Lineage</strong></h6>';

        // Chronological order: ancestors, the clicked polygon, descendants.
        ['before', 'self', 'after', 'related'].forEach(role => {
            const n = counts[role];
            if (!n) return;   // hide roles absent from this result
            const style = LINEAGE_ROLE_STYLES[role];
            html += `
                <div class="legend-item">
                    <span class="legend-color" style="background-color: ${style.fill};
                          border-color: ${style.border};"></span>
                    ${style.label} (${n})
                </div>
            `;
        });

        if (meta.truncated) {
            html += `<div class="legend-item text-muted">
                        Truncated - ${meta.total} in full lineage
                     </div>`;
        }

        div.innerHTML = html;
        return div;
    };
    lineageLegend.addTo(map);
}

/**
 * Remove the lineage legend if present.
 */
function removeLineageLegend() {
    if (lineageLegend) {
        map.removeControl(lineageLegend);
        lineageLegend = null;
    }
}

/**
 * Calculate the centroid of a single polygon ring as [lng, lat].
 */
function getPolygonCentroid(coords) {
    let sumX = 0, sumY = 0;
    for (let i = 0; i < coords.length - 1; i++) {
        sumX += coords[i][0];
        sumY += coords[i][1];
    }
    const count = coords.length - 1;
    if (count <= 0) return null;
    return [sumX / count, sumY / count];
}

/**
 * Get a representative centroid [lng, lat] for a GeoJSON feature.
 */
function getFeatureCentroid(feature) {
    const props = feature.properties || {};

    // Prefer explicit lon/lat columns when present and valid.
    const lon = parseFloat(props.lon);
    const lat = parseFloat(props.lat);
    if (!isNaN(lon) && !isNaN(lat)) {
        return [lon, lat];
    }

    const geom = feature.geometry;
    if (!geom || !geom.coordinates) return null;

    if (geom.type === 'Polygon') {
        return getPolygonCentroid(geom.coordinates[0]);
    }

    if (geom.type === 'MultiPolygon') {
        // Use the outer ring of the first polygon part.
        const firstPart = geom.coordinates[0];
        if (firstPart && firstPart[0]) {
            return getPolygonCentroid(firstPart[0]);
        }
    }

    return null;
}

/**
 * Clear lineage layer
 */
function clearLineageLayer() {
    if (lineageLayer) {
        map.removeLayer(lineageLayer);
        lineageLayer = null;
        currentLineageData = null;
    }

    removeLineageLegend();

    // Reset Track Lineage button if present
    const trackLineageBtn = document.getElementById('trackLineageBtn');
    if (trackLineageBtn) {
        trackLineageBtn.classList.remove('active');
        trackLineageBtn.textContent = 'Track Lineage';
        // Re-enable if current feature has inst
        if (currentInspectedFeature && currentInspectedFeature.properties && currentInspectedFeature.properties.inst) {
            trackLineageBtn.disabled = false;
        } else {
            trackLineageBtn.disabled = true;
        }
    }

    // Restore WMS layer
    if (wmsLayer && !wmsLayer._map) {
        wmsLayer.addTo(map);
    }
}

/**
 * Get color based on calving location
 */
function getColorForCalvingLoc(calvingLoc) {
    const colors = {
        'CG': '#90de4c',
        'NA': '#40d77a',
        'NG': '#debd76',
        'PG': '#6154da',
        'RG': '#dc25e6',
        'SG': '#d51c3e'
    };
    return colors[calvingLoc] || '#79bace';
}

/**
 * Add legend to map
 */
function addLegend() {
    const legend = L.control({ position: 'bottomright' });

    legend.onAdd = function(map) {
        const div = L.DomUtil.create('div', 'legend');
        div.innerHTML = `
            <h6><strong>Calving Location</strong></h6>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #90de4c;"></span> CG - C.H. Ostenfeld Glacier
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #40d77a;"></span> NA - Not Available
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #debd76;"></span> NG - North Greenland
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #6154da;"></span> PG - Petermann Glacier
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #dc25e6;"></span> RG - Ryder Glacier
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #d51c3e;"></span> SG - Steensby Glacier
            </div>
        `;
        return div;
    };

    legend.addTo(map);
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    const indicator = document.getElementById('loadingIndicator');
    if (show) {
        indicator.classList.add('active');
    } else {
        indicator.classList.remove('active');
    }
}

// Initialize map when page loads
document.addEventListener('DOMContentLoaded', function() {
    initMap();
});