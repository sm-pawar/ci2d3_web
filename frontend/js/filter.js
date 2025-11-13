/**
 * CI2D3 Ice Island Explorer - Filter Module
 * Handles attribute-based filtering of ice islands
 */

/**
 * Apply filter based on form inputs
 */
async function applyFilter(event) {
    event.preventDefault();

    const field = document.getElementById('filterField').value;
    const operator = document.getElementById('filterOperator').value;
    const value = document.getElementById('filterValue').value;

    if (!field || !operator || !value) {
        alert('Please fill in all filter fields');
        return;
    }

    // Determine value type based on field
    let processedValue = value;

    // Convert numeric fields
    const numericFields = ['carving_year', 'area_km2', 'perimeter_km', 'max_length_km', 'thickness_m', 'objectid', 'gid'];
    if (numericFields.includes(field)) {
        processedValue = parseFloat(value);
        if (isNaN(processedValue)) {
            alert('Please enter a valid number for this field');
            return;
        }
    }

    // Build filter request
    const filterRequest = {
        field: field,
        operator: operator,
        value: processedValue
    };

    showLoading(true);

    try {
        const response = await fetch(`${CONFIG.apiUrl}/filter/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(filterRequest)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Display results
        displayFilterResults(data);

        // Add filtered layer to map
        if (data.features && data.features.length > 0) {
            addFilteredLayer(data);
        } else {
            showFilterMessage('No features match the filter criteria', 'warning');
        }

    } catch (error) {
        console.error('Error applying filter:', error);
        showFilterMessage(`Error: ${error.message}`, 'danger');
    } finally {
        showLoading(false);
    }
}

/**
 * Display filter results summary
 */
function displayFilterResults(data) {
    const resultsDiv = document.getElementById('filterResults');

    if (data.count > 0) {
        resultsDiv.innerHTML = `
            <div class="alert alert-success mb-0" role="alert">
                <strong>Filter Applied!</strong><br>
                Found <span class="result-count">${data.count}</span> matching ice island(s)
            </div>
        `;
    } else {
        resultsDiv.innerHTML = `
            <div class="alert alert-warning mb-0" role="alert">
                <strong>No Results</strong><br>
                No ice islands match the filter criteria
            </div>
        `;
    }

    resultsDiv.classList.add('active');
}

/**
 * Show filter message
 */
function showFilterMessage(message, type = 'info') {
    const resultsDiv = document.getElementById('filterResults');
    resultsDiv.innerHTML = `
        <div class="alert alert-${type} mb-0" role="alert">
            ${message}
        </div>
    `;
    resultsDiv.classList.add('active');
}

/**
 * Clear filter and restore original layer
 */
function clearFilter() {
    // Reset form
    document.getElementById('filterForm').reset();

    // Clear results
    const resultsDiv = document.getElementById('filterResults');
    resultsDiv.classList.remove('active');
    resultsDiv.innerHTML = '';

    // Clear filtered layer on map
    clearFilteredLayer();
}

/**
 * Toggle filter panel visibility
 */
function toggleFilterPanel() {
    const panel = document.getElementById('filterPanel');
    const mapContainer = document.getElementById('mapContainer');

    panel.classList.toggle('hidden');

    // Adjust map container width
    if (panel.classList.contains('hidden')) {
        mapContainer.classList.remove('col-md-9');
        mapContainer.classList.add('col-md-12');
    } else {
        mapContainer.classList.remove('col-md-12');
        mapContainer.classList.add('col-md-9');
    }

    // Invalidate map size to handle resize
    setTimeout(() => {
        if (map) {
            map.invalidateSize();
        }
    }, 300);
}

/**
 * Update operator options based on selected field type
 */
function updateOperatorOptions() {
    const fieldSelect = document.getElementById('filterField');
    const operatorSelect = document.getElementById('filterOperator');
    const selectedOption = fieldSelect.options[fieldSelect.selectedIndex];

    if (!selectedOption || !selectedOption.dataset.type) {
        return;
    }

    const dataType = selectedOption.dataset.type;

    // Clear existing options
    operatorSelect.innerHTML = '';

    let operators = [];

    // Determine appropriate operators based on data type
    if (dataType.includes('int') || dataType.includes('float') || dataType.includes('numeric')) {
        // Numeric fields
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: '>', text: '>' },
            { value: '<', text: '<' },
            { value: '>=', text: '>=' },
            { value: '<=', text: '<=' }
        ];
    } else if (dataType.includes('char') || dataType.includes('text')) {
        // Text fields
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: 'LIKE', text: 'LIKE' },
            { value: 'ILIKE', text: 'ILIKE (case-insensitive)' }
        ];
    } else if (dataType.includes('date') || dataType.includes('time')) {
        // Date/time fields
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: '>', text: 'after' },
            { value: '<', text: 'before' },
            { value: '>=', text: 'on or after' },
            { value: '<=', text: 'on or before' }
        ];
    } else {
        // Default operators
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: 'LIKE', text: 'LIKE' }
        ];
    }

    // Add operator options
    operators.forEach(op => {
        const option = document.createElement('option');
        option.value = op.value;
        option.textContent = op.text;
        operatorSelect.appendChild(option);
    });
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    // Filter form submission
    document.getElementById('filterForm').addEventListener('submit', applyFilter);

    // Clear filter button
    document.getElementById('clearFilter').addEventListener('click', clearFilter);

    // Toggle filter panel
    document.getElementById('toggleFilter').addEventListener('click', function(e) {
        e.preventDefault();
        toggleFilterPanel();
    });

    // Close filter panel
    document.getElementById('closeFilter').addEventListener('click', function() {
        toggleFilterPanel();
    });

    // Update operators when field changes
    document.getElementById('filterField').addEventListener('change', updateOperatorOptions);

    // About button
    document.getElementById('aboutBtn').addEventListener('click', function(e) {
        e.preventDefault();
        alert(`CI2D3 Ice Island Explorer v1.0

A web-based GIS portal for visualizing and exploring Canadian Ice Island data.

Features:
- Interactive map with ice island locations
- Attribute-based filtering
- Feature inspection
- WMS/WFS layer support

Powered by:
- Leaflet.js
- GeoServer
- PostGIS
- Flask`);
    });

    // Layers toggle (placeholder)
    document.getElementById('toggleLayers').addEventListener('click', function(e) {
        e.preventDefault();
        alert('Layer control is available in the top-right corner of the map');
    });
});
