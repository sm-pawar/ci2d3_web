/**
 * CI2D3 Ice Island Explorer - Filter Module
 * Handles attribute-based filtering of ice islands
 */

// Array to store active filter conditions
let filterConditions = [];

// Descriptions for each attribute
const fieldDescriptions = {
    'calvingyr': 'The year the ice island calved from the glacier.',
    'calvingloc': 'Location code indicating where the ice island originated (e.g., PG for Petermann Glacier).',
    'area': 'Area of the ice island in square kilometers (km²).',
    'scenedate': 'Date of the satellite scene used for this observation.',
    'imgref': 'Reference identifier for the satellite image.',
    'sensor': 'Satellite sensor used to capture the image (e.g., MODIS, Landsat).'
};

/**
 * Update the description box based on selected field
 */
function updateFieldDescription() {
    const fieldSelect = document.getElementById('filterField');
    const descDiv = document.getElementById('fieldDescription');
    const selectedValue = fieldSelect.value;
    if (selectedValue && fieldDescriptions[selectedValue]) {
        descDiv.textContent = fieldDescriptions[selectedValue];
    } else {
        descDiv.textContent = '';
    }
}

/**
 * Apply filter based on form inputs (single or additional)
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
    const numericFields = ['area', 'perimeter', 'length', 'lon', 'lat', 'gid'];
    if (numericFields.includes(field)) {
        processedValue = parseFloat(value);
        if (isNaN(processedValue)) {
            alert('Please enter a valid number for this field');
            return;
        }
    }

    // Build new filter condition
    const newCondition = {
        field: field,
        operator: operator,
        value: processedValue
    };

    // Add to conditions array
    filterConditions.push(newCondition);

    // Build request payload with all filters
    const filterRequest = {
        filters: filterConditions
    };

    // Update button text if more than one filter
    updateFilterButtonText();

    // Show active filters summary
    updateActiveFiltersSummary();

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

        // Add filtered layer to map (will clear previous filtered layer)
        if (data.features && data.features.length > 0) {
            addFilteredLayer(data);
        } else {
            showFilterMessage('No features match the combined filter criteria', 'warning');
        }

    } catch (error) {
        console.error('Error applying filter:', error);
        showFilterMessage(`Error: ${error.message}`, 'danger');
        // Remove the condition if the request failed
        filterConditions.pop();
        updateFilterButtonText();
        updateActiveFiltersSummary();
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
                No ice islands match the combined filter criteria
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
 * Update the Apply/Additional Filter button text based on number of active filters
 */
function updateFilterButtonText() {
    const btn = document.getElementById('applyFilterBtn');
    if (filterConditions.length === 0) {
        btn.textContent = 'Apply Filter';
    } else {
        btn.textContent = `Additional Filter (${filterConditions.length})`;
    }
}

/**
 * Update the summary of active filters
 */
function updateActiveFiltersSummary() {
    const summaryDiv = document.getElementById('activeFiltersSummary');
    if (filterConditions.length === 0) {
        summaryDiv.innerHTML = '';
        return;
    }

    let html = '<div class="alert alert-info mb-0 small"><strong>Active Filters:</strong><ul class="mb-0">';
    filterConditions.forEach((cond, idx) => {
        html += `<li>${cond.field} ${cond.operator} ${cond.value}</li>`;
    });
    html += '</ul></div>';
    summaryDiv.innerHTML = html;
}

/**
 * Clear filter and restore original layer
 */
function clearFilter() {
    // Reset form
    document.getElementById('filterForm').reset();
    // Clear the value input to default placeholder
    document.getElementById('filterValue').value = '';

    // Reset conditions
    filterConditions = [];
    updateFilterButtonText();
    updateActiveFiltersSummary();

    // Clear results
    const resultsDiv = document.getElementById('filterResults');
    resultsDiv.classList.remove('active');
    resultsDiv.innerHTML = '';

    // Clear filtered layer on map (this also clears lineage layer)
    clearFilteredLayer();

    // Reset Track Lineage button if visible
    const trackLineageBtn = document.getElementById('trackLineageBtn');
    if (trackLineageBtn) {
        trackLineageBtn.classList.remove('active');
        trackLineageBtn.textContent = 'Track Lineage';
        trackLineageBtn.disabled = true;
    }

    // Ensure the attribute description is cleared
    updateFieldDescription();
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

    // Update description
    updateFieldDescription();

    if (!selectedOption || !selectedOption.value) {
        operatorSelect.innerHTML = '';
        return;
    }

    const dataType = selectedOption.dataset.type || selectedOption.getAttribute('data-type');

    if (!dataType) {
        console.error('No data-type attribute found!');
        operatorSelect.innerHTML = '';
        return;
    }

    operatorSelect.innerHTML = '';
    let operators = [];

    if (dataType.includes('numeric') || dataType.includes('int') || dataType.includes('float') || dataType.includes('double')) {
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: '>', text: '>' },
            { value: '<', text: '<' },
            { value: '>=', text: '>=' },
            { value: '<=', text: '<=' }
        ];
    } else if (dataType.includes('char') || dataType.includes('text') || dataType.includes('varying')) {
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: 'LIKE', text: 'LIKE' },
            { value: 'ILIKE', text: 'ILIKE (case-insensitive)' }
        ];
    } else if (dataType.includes('date') || dataType.includes('time')) {
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: '>', text: 'after' },
            { value: '<', text: 'before' },
            { value: '>=', text: 'on or after' },
            { value: '<=', text: 'on or before' }
        ];
    } else {
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: 'LIKE', text: 'LIKE' }
        ];
    }

    operators.forEach(op => {
        const option = document.createElement('option');
        option.value = op.value;
        option.textContent = op.text;
        operatorSelect.appendChild(option);
    });

    // If we have a default value, set it (e.g., for area we want '>')
    if (fieldSelect.value === 'area') {
        operatorSelect.value = '>';
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    const filterField = document.getElementById('filterField');
    const filterForm = document.getElementById('filterForm');
    const clearFilterBtn = document.getElementById('clearFilter');
    const closeFilterBtn = document.getElementById('closeFilter');

    if (filterForm) {
        filterForm.addEventListener('submit', applyFilter);
    }

    if (clearFilterBtn) {
        clearFilterBtn.addEventListener('click', clearFilter);
    }

    if (closeFilterBtn) {
        closeFilterBtn.addEventListener('click', function() {
            toggleFilterPanel();
        });
    }

    if (filterField) {
        filterField.addEventListener('change', updateOperatorOptions);
        // Initialize operators and description on load
        updateOperatorOptions();
        // Set default operator for area
        setTimeout(() => {
            const operatorSelect = document.getElementById('filterOperator');
            if (operatorSelect && filterField.value === 'area') {
                operatorSelect.value = '>';
            }
        }, 100);
    }
});