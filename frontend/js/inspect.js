/**
 * CI2D3 Ice Island Explorer - Inspect Module
 * Handles feature inspection and information display
 */

/**
 * Display feature information in the inspect panel
 */
function displayFeatureInfo(feature) {
    const panel = document.getElementById('inspectPanel');
    const content = document.getElementById('inspectContent');

    if (!feature || !feature.properties) {
        content.innerHTML = '<p class="text-muted">No feature data available</p>';
        return;
    }

    const props = feature.properties;

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

/**
 * Get available attributes from API
 */
async function fetchAttributes() {
    try {
        const response = await fetch(`${CONFIG.apiUrl}/inspect/attributes`);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        populateAttributeSelect(data.attributes);

    } catch (error) {
        console.error('Error fetching attributes:', error);
    }
}

/**
 * Populate filter field select with available attributes
 */
function populateAttributeSelect(attributes) {
    const select = document.getElementById('filterField');

    // Clear existing options except the first one
    while (select.options.length > 1) {
        select.remove(1);
    }

    // Add attribute options
    attributes.forEach(attr => {
        if (attr.name !== 'geom' && attr.name !== 'gid') {
            const option = document.createElement('option');
            option.value = attr.name;
            option.textContent = formatPropertyLabel(attr.name);
            option.dataset.type = attr.data_type;
            select.appendChild(option);
        }
    });
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Close inspect panel button
    document.getElementById('closeInspect').addEventListener('click', closeInspectPanel);

    // Fetch available attributes
    fetchAttributes();
});
