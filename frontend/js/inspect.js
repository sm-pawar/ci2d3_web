/**
 * CI2D3 Ice Island Explorer - Inspect Module
 * Handles feature inspection and information display
 */

// Store the currently inspected feature for lineage tracking
let currentInspectedFeature = null;

/**
 * Display feature information in the inspect panel
 */
function displayFeatureInfo(feature) {
    const panel = document.getElementById('inspectPanel');
    const content = document.getElementById('inspectContent');
    const trackLineageBtn = document.getElementById('trackLineageBtn');

    if (!feature || !feature.properties) {
        content.innerHTML = '<p class="text-muted">No feature data available</p>';
        currentInspectedFeature = null;
        if (trackLineageBtn) {
            trackLineageBtn.disabled = true;
            trackLineageBtn.classList.remove('active');
            trackLineageBtn.textContent = 'Track Lineage';
        }
        return;
    }

    // Store the current feature for lineage tracking
    currentInspectedFeature = feature;

    const props = feature.properties;

    // Enable the Track Lineage button if the feature has an instance id.
    // Lineage tracking walks the parent/child graph starting from `inst`,
    // so any feature with an `inst` can have its lineage tree resolved.
    if (trackLineageBtn) {
        trackLineageBtn.disabled = !props.inst;
        trackLineageBtn.classList.remove('active');
        trackLineageBtn.textContent = 'Track Lineage';
    }

    // Build HTML for feature properties
    let html = '<div class="feature-info">';

    // Add each property
    for (const [key, value] of Object.entries(props)) {
        // Skip null/undefined values and geometry-related fields
        if (value === null || value === undefined || key === 'geom') {
            continue;
        }

        // Format the key as a readable label
        const label = formatPropertyLabel(key);

        // Format the value
        const formattedValue = formatPropertyValue(key, value);

        html += `
            <div class="feature-property">
                <div class="property-label">${label}</div>
                <div class="property-value">${formattedValue}</div>
            </div>
        `;
    }

    html += '</div>';

    content.innerHTML = html;
    panel.classList.add('active');
}

/**
 * Format property label for display
 */
function formatPropertyLabel(key) {
    // Convert snake_case to Title Case
    return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, char => char.toUpperCase());
}

/**
 * Format property value based on type and key
 */
function formatPropertyValue(key, value) {
    // Handle different data types and special cases

    // Dates
    if (key.toLowerCase().includes('date') && value) {
        const date = new Date(value);
        if (!isNaN(date.getTime())) {
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric'
            });
        }
    }

    // Numbers with units
    if (key === 'area_km2') {
        return `${parseFloat(value).toFixed(2)} km²`;
    }
    if (key === 'perimeter_km' || key === 'max_length_km' || key === 'max_width_km') {
        return `${parseFloat(value).toFixed(2)} km`;
    }
    if (key === 'thickness_m') {
        return `${parseFloat(value).toFixed(1)} m`;
    }

    // Calving location with color
    if (key === 'calvingloc') {
        const color = getColorForCalvingLoc(value);
        return `<span style="color: ${color}; font-weight: bold;">${value}</span> - ${getCalvingLocationName(value)}`;
    }

    // Lineage relationship to the clicked polygon, colour-matched to the map
    if (key === 'lineage_role') {
        const style = (typeof LINEAGE_ROLE_STYLES !== 'undefined')
            ? LINEAGE_ROLE_STYLES[value]
            : null;
        if (style) {
            return `<span style="color: ${style.border}; font-weight: bold;">${style.label}</span>`;
        }
        return value;
    }

    // Boolean values
    if (typeof value === 'boolean') {
        return value ? 'Yes' : 'No';
    }

    // Numbers
    if (typeof value === 'number') {
        return value.toLocaleString();
    }

    // Default: return as string
    return value;
}

/**
 * Get full name for calving location code
 */
function getCalvingLocationName(code) {
    const names = {
        'CG': 'Central Glacier',
        'NA': 'North America',
        'NG': 'Northern Glacier',
        'PG': 'Petermann Glacier',
        'RG': 'Ryder Glacier',
        'SG': 'Southern Glacier'
    };
    return names[code] || 'Unknown';
}

/**
 * Close inspect panel
 */
function closeInspectPanel() {
    const panel = document.getElementById('inspectPanel');
    panel.classList.remove('active');

    // Reset the Track Lineage button state
    const trackLineageBtn = document.getElementById('trackLineageBtn');
    if (trackLineageBtn) {
        trackLineageBtn.classList.remove('active');
        trackLineageBtn.textContent = 'Track Lineage';
    }
}

/**
 * Track lineage for the currently inspected feature.
 *
 * Walks the parent/child lineage graph starting from the selected feature's
 * `inst` and displays every ice island polygon in the same rooted lineage
 * tree on the map. Backed by the /api/lineage endpoint, which ports the
 * graph-traversal logic from the reference analysis code (ci2d3.py).
 */
async function trackLineage() {
    if (!currentInspectedFeature || !currentInspectedFeature.properties) {
        console.error('No feature selected for lineage tracking');
        return;
    }

    const props = currentInspectedFeature.properties;

    // The lineage graph is keyed on the instance id (`inst`).
    const inst = props.inst;

    if (!inst) {
        alert('This ice island has no instance id (inst); lineage cannot be tracked.');
        return;
    }

    const trackLineageBtn = document.getElementById('trackLineageBtn');

    showLoading(true);

    try {
        // "chain" = this polygon's own lineage line: all of its ancestors plus
        // all of its descendants. (mode "all" would return the entire connected
        // component, which averages ~2,800 polygons on this dataset.)
        const response = await fetch(`${CONFIG.apiUrl}/lineage/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ inst: inst, mode: 'chain' })
        });

        if (!response.ok) {
            // A 404 here means the API container is still running a build
            // without the lineage blueprint registered.
            if (response.status === 404) {
                throw new Error(
                    'The /api/lineage endpoint was not found. The Flask API is ' +
                    'running an older build - restart it with: ' +
                    'docker-compose restart flask-api'
                );
            }
            let message = `HTTP error! status: ${response.status}`;
            try {
                const err = await response.json();
                if (err.message) message = err.message;
            } catch (e) { /* ignore parse errors */ }
            throw new Error(message);
        }

        const data = await response.json();

        if (data.features && data.features.length > 0) {
            // Add lineage layer to map with special styling
            addLineageLayer(data, inst);

            const meta = data.lineage || {};

            // Update button to show active state
            if (trackLineageBtn) {
                trackLineageBtn.classList.add('active');
                trackLineageBtn.textContent = meta.truncated
                    ? `Showing ${data.count} of ${meta.total} in lineage`
                    : `Showing ${data.count} in lineage`;
            }

            console.log(
                `Lineage of ${inst}: showing ${data.count}` +
                (meta.total ? ` of ${meta.total} total` : '') +
                (meta.truncated ? ' (truncated)' : '')
            );
        } else {
            alert('No related ice islands found in this lineage');
        }

    } catch (error) {
        console.error('Error tracking lineage:', error);
        alert(`Error tracking lineage: ${error.message}`);
    } finally {
        showLoading(false);
    }
}

/**
 * Fetch feature by ID from API
 */
async function fetchFeatureById(featureId) {
    showLoading(true);

    try {
        const response = await fetch(`${CONFIG.apiUrl}/inspect/${featureId}`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const feature = await response.json();
        displayFeatureInfo(feature);

    } catch (error) {
        console.error('Error fetching feature:', error);
        const content = document.getElementById('inspectContent');
        content.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <strong>Error:</strong> Failed to load feature information.
                <br><small>${error.message}</small>
            </div>
        `;
    } finally {
        showLoading(false);
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Close inspect panel button
    document.getElementById('closeInspect').addEventListener('click', closeInspectPanel);

    // Track Lineage button
    const trackLineageBtn = document.getElementById('trackLineageBtn');
    if (trackLineageBtn) {
        trackLineageBtn.addEventListener('click', trackLineage);
    }
});
