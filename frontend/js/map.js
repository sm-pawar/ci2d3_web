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
let currentFilteredData = null;

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
        'OpenStreetMap': L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
            maxZoom: 19,
            pane: 'basemapPane'
        }),
        'CartoDB Positron': L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19,
            pane: 'basemapPane'
        }),
        'ESRI World Imagery': L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community',
            maxZoom: 18,
            pane: 'basemapPane'
        })
    };

    // Add default base layer
    baseLayers['CartoDB Positron'].addTo(map);

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
        'Ice Islands (CI2D3)': wmsLayer
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

    const url = `${CONFIG.geoserverUrl}/wms?${new URLSearchParams(params)}`;

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
                <span class="legend-color" style="background-color: #90de4c;"></span> CG - C. Glacier
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #40d77a;"></span> NA - N. America
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #debd76;"></span> NG - N. Glacier
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #6154da;"></span> PG - Petermann G.
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #dc25e6;"></span> RG - R. Glacier
            </div>
            <div class="legend-item">
                <span class="legend-color" style="background-color: #d51c3e;"></span> SG - S. Glacier
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
