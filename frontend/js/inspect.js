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

    // If lineage is currently displayed, clear it (as per requirement)
    if (lineageLayer) {
        clearLineageLayer();
        // Reset button state (will be updated below)
    }

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
    if (trackLineageBtn) {
        trackLineageBtn.disabled = !props.inst;
        trackLineageBtn.classList.remove('active');
        trackLineageBtn.textContent = 'Track Lineage';
    }

    // Build HTML for feature properties
    let html = '<div class="feature-info">';

    for (const [key, value] of Object.entries(props)) {
        if (value === null || value === undefined || key === 'geom') {
            continue;
        }
        const label = formatPropertyLabel(key);
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
    return key
        .replace(/_/g, ' ')
        .replace(/\b\w/g, char => char.toUpperCase());
}

/**
 * Format property value based on type and key
 */
function formatPropertyValue(key, value) {
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

    if (key === 'area_km2') {
        return `${parseFloat(value).toFixed(2)} km²`;
    }
    if (key === 'perimeter_km' || key === 'max_length_km' || key === 'max_width_km') {
        return `${parseFloat(value).toFixed(2)} km`;
    }
    if (key === 'thickness_m') {
        return `${parseFloat(value).toFixed(1)} m`;
    }

    if (key === 'calvingloc') {
        const color = getColorForCalvingLoc(value);
        return `<span style="color: ${color}; font-weight: bold;">${value}</span> - ${getCalvingLocationName(value)}`;
    }

    if (key === 'lineage_role') {
        const style = (typeof LINEAGE_ROLE_STYLES !== 'undefined')
            ? LINEAGE_ROLE_STYLES[value]
            : null;
        if (style) {
            return `<span style="color: ${style.border}; font-weight: bold;">${style.label}</span>`;
        }
        return value;
    }

    if (typeof value === 'boolean') {
        return value ? 'Yes' : 'No';
    }

    if (typeof value === 'number') {
        return value.toLocaleString();
    }

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

    const trackLineageBtn = document.getElementById('trackLineageBtn');
    if (trackLineageBtn) {
        trackLineageBtn.classList.remove('active');
        trackLineageBtn.textContent = 'Track Lineage';
    }
}

/**
 * Handle the Track Lineage / Clear Lineage button click
 */
function handleTrackLineageClick() {
    const btn = document.getElementById('trackLineageBtn');
    // If lineage layer exists, clear it
    if (lineageLayer) {
        clearLineageLayer();
        btn.textContent = 'Track Lineage';
        btn.classList.remove('active');
        // Re-enable based on current feature
        if (currentInspectedFeature && currentInspectedFeature.properties && currentInspectedFeature.properties.inst) {
            btn.disabled = false;
        } else {
            btn.disabled = true;
        }
    } else {
        // Otherwise track lineage
        trackLineage();
    }
}

/**
 * Track lineage for the currently inspected feature.
 */
async function trackLineage() {
    if (!currentInspectedFeature || !currentInspectedFeature.properties) {
        console.error('No feature selected for lineage tracking');
        return;
    }

    const props = currentInspectedFeature.properties;
    const inst = props.inst;

    if (!inst) {
        alert('This ice island has no instance id (inst); lineage cannot be tracked.');
        return;
    }

    const trackLineageBtn = document.getElementById('trackLineageBtn');

    showLoading(true);

    try {
        const response = await fetch(`${CONFIG.apiUrl}/lineage/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ inst: inst, mode: 'chain' })
        });

        if (!response.ok) {
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
            } catch (e) { /* ignore */ }
            throw new Error(message);
        }

        const data = await response.json();

        if (data.features && data.features.length > 0) {
            addLineageLayer(data, inst);
            const meta = data.lineage || {};

            // Change button to "Clear Lineage"
            trackLineageBtn.classList.add('active');
            trackLineageBtn.textContent = meta.truncated
                ? `Showing ${data.count} of ${meta.total} in lineage`
                : `Showing ${data.count} in lineage`;

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
    document.getElementById('closeInspect').addEventListener('click', closeInspectPanel);

    const trackLineageBtn = document.getElementById('trackLineageBtn');
    if (trackLineageBtn) {
        trackLineageBtn.addEventListener('click', handleTrackLineageClick);
    }
});