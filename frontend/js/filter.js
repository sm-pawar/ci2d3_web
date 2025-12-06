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

    // Convert numeric fields (based on actual database schema)
    const numericFields = ['area', 'perimeter', 'length', 'lon', 'lat', 'gid'];
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

    // If no valid option selected (e.g., "Select attribute..."), clear operators
    if (!selectedOption || !selectedOption.value || !selectedOption.dataset.type) {
        operatorSelect.innerHTML = '';
        return;
    }

    const dataType = selectedOption.dataset.type;
    console.log('Selected field:', selectedOption.value, 'Data type:', dataType);

    // Clear existing options
    operatorSelect.innerHTML = '';

    let operators = [];

    // Determine appropriate operators based on data type
    if (dataType.includes('numeric') || dataType.includes('int') || dataType.includes('float') || dataType.includes('double')) {
        // Numeric fields
        console.log('Using numeric operators');
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: '>', text: '>' },
            { value: '<', text: '<' },
            { value: '>=', text: '>=' },
            { value: '<=', text: '<=' }
        ];
    } else if (dataType.includes('char') || dataType.includes('text') || dataType.includes('varying')) {
        // Text fields
        console.log('Using text operators');
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: 'LIKE', text: 'LIKE' },
            { value: 'ILIKE', text: 'ILIKE (case-insensitive)' }
        ];
    } else if (dataType.includes('date') || dataType.includes('time')) {
        // Date/time fields
        console.log('Using date operators');
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: '>', text: 'after' },
            { value: '<', text: 'before' },
            { value: '>=', text: 'on or after' },
            { value: '<=', text: 'on or before' }
        ];
    } else {
        // Default operators (fallback)
        console.log('Using default operators for unknown type:', dataType);
        operators = [
            { value: '=', text: '=' },
            { value: '!=', text: '!=' },
            { value: 'LIKE', text: 'LIKE' }
        ];
    }

    console.log('Adding', operators.length, 'operators');

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
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', applyFilter);
    }

    // Clear filter button
    const clearFilterBtn = document.getElementById('clearFilter');
    if (clearFilterBtn) {
        clearFilterBtn.addEventListener('click', clearFilter);
    }

    // Close filter panel button
    const closeFilterBtn = document.getElementById('closeFilter');
    if (closeFilterBtn) {
        closeFilterBtn.addEventListener('click', function() {
            toggleFilterPanel();
        });
    }

    // Update operators when field changes
    const filterField = document.getElementById('filterField');
    if (filterField) {
        filterField.addEventListener('change', updateOperatorOptions);

        // Initialize operators on page load based on first selection
        // This ensures operators are populated even before user changes field
        if (filterField.options.length > 1) {
            // Trigger update for the first real option (skip "Select attribute...")
            updateOperatorOptions.call(filterField);
        }
    }
});
