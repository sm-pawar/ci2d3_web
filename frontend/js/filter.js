/**
 * CI2D3 Ice Island Explorer - Filter Module
 * Handles attribute-based filtering of ice islands
 */

/**
 * Metadata for each filterable attribute.
 *
 * Drives the operator list, the value control (dropdown vs free text) and the
 * help text, so the form only ever offers combinations that make sense for
 * the underlying column.
 */
const EQUALITY_OPERATORS = [
    { value: '=', text: '=' },
    { value: '!=', text: '!=' }
];

const NUMERIC_OPERATORS = [
    { value: '=', text: '=' },
    { value: '!=', text: '!=' },
    { value: '>', text: '>' },
    { value: '<', text: '<' },
    { value: '>=', text: '>=' },
    { value: '<=', text: '<=' }
];

const FIELD_META = {
    calvingyr: {
        description: 'The year the ice island calved from its source location.',
        operators: EQUALITY_OPERATORS,
        // "NA" is included because it covers 7,456 observations (29.4% of the
        // database) and is listed as a valid calving year in the project's own
        // constants (ref/python/defs.py). The data also contains 30 records
        // with calvingyr "2013", which is deliberately not offered here - add
        // an option below if those should be filterable too.
        options: [
            { value: '2008', label: '2008' },
            { value: '2010', label: '2010' },
            { value: '2011', label: '2011' },
            { value: '2012', label: '2012' },
            { value: 'NA', label: 'NA - Not Available' }
        ]
    },
    calvingloc: {
        description: 'Location code indicating where the ice island originated.',
        operators: EQUALITY_OPERATORS,
        options: [
            { value: 'PG', label: 'PG - Petermann Glacier' },
            { value: 'RG', label: 'RG - Ryder Glacier' },
            { value: 'SG', label: 'SG - Steensby Glacier' },
            { value: 'CG', label: 'CG - C.H. Ostenfeld Glacier' },
            { value: 'NG', label: 'NG - North Greenland' },
            { value: 'NA', label: 'NA - Not Available' }
        ]
    },
    area: {
        description: 'Area of the ice island in square kilometers (km²).',
        operators: NUMERIC_OPERATORS,
        numeric: true,
        placeholder: 'e.g. 100',
        defaultValue: '100',
        defaultOperator: '>'
    },
    scenedate: {
        // scenedate is stored as text including a time component
        // (e.g. "2010-10-10 15:34:49"), so LIKE is the only operator that
        // usefully matches a plain YYYY-MM-DD date.
        description: 'Date of the satellite scene in which the ice island was ' +
                     'observed, in YYYY-MM-DD.',
        operators: [{ value: 'LIKE', text: 'LIKE' }],
        placeholder: 'e.g. 2010-10-10',
        valueHelp: 'Operator and Value example: LIKE 2010-10-10'
    },
    sensor: {
        description: 'Satellite sensor used to capture the image.',
        operators: EQUALITY_OPERATORS,
        options: [
            { value: 'r1', label: 'r1 - Radarsat-1' },
            { value: 'r2', label: 'r2 - Radarsat-2' },
            { value: 'es', label: 'es - Envisat' },
            { value: 'al', label: 'al - Advanced Land Imager' }
        ]
    }
};

/**
 * Filters currently applied to the map, combined with AND.
 * "Apply Filter" replaces this list; "Additional Filter" appends to it.
 */
let activeFilters = [];

/**
 * Read the current attribute/operator/value selection from the form.
 * Returns null (after alerting) if the selection is incomplete or invalid.
 */
function readFilterInput() {
    const field = document.getElementById('filterField').value;
    const operator = document.getElementById('filterOperator').value;
    const meta = FIELD_META[field];

    if (!field || !operator || !meta) {
        alert('Please select an attribute and operator');
        return null;
    }

    // The value comes from whichever control is visible for this attribute.
    const valueSelect = document.getElementById('filterValueSelect');
    const valueInput = document.getElementById('filterValue');
    const usingSelect = !valueSelect.classList.contains('d-none');
    const rawValue = usingSelect ? valueSelect.value : valueInput.value.trim();

    if (!rawValue) {
        alert('Please enter or select a value');
        return null;
    }

    let value = rawValue;
    if (meta.numeric) {
        value = parseFloat(rawValue);
        if (isNaN(value)) {
            alert('Please enter a valid number for this field');
            return null;
        }
    }

    return { field: field, operator: operator, value: value };
}

/**
 * Run the current activeFilters against the API and update the map.
 */
async function runFilterQuery() {
    if (activeFilters.length === 0) {
        return;
    }

    // A single filter uses the simple request shape; multiple filters are
    // combined server-side with AND.
    const body = activeFilters.length === 1
        ? activeFilters[0]
        : { filters: activeFilters, logic: 'AND' };

    showLoading(true);

    try {
        const response = await fetch(`${CONFIG.apiUrl}/filter/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            let message = `HTTP error! status: ${response.status}`;
            try {
                const err = await response.json();
                if (err.message) message = err.message;
            } catch (e) { /* ignore parse errors */ }
            throw new Error(message);
        }

        const data = await response.json();

        displayFilterResults(data);

        if (data.features && data.features.length > 0) {
            addFilteredLayer(data);
        } else {
            // Nothing matched - drop the layer so the map isn't showing a
            // stale result alongside a "no results" message.
            clearFilteredLayer();
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
 * Apply Filter - replace any existing filters with the current selection.
 */
async function applyFilter(event) {
    if (event) {
        event.preventDefault();
    }

    const filter = readFilterInput();
    if (!filter) return;

    activeFilters = [filter];
    renderActiveFilters();
    await runFilterQuery();
}

/**
 * Additional Filter - add the current selection to the existing filters.
 */
async function addAdditionalFilter() {
    const filter = readFilterInput();
    if (!filter) return;

    // With nothing applied yet this behaves the same as "Apply Filter".
    activeFilters.push(filter);
    renderActiveFilters();
    await runFilterQuery();
}

/**
 * Remove one applied filter and re-run the query.
 */
async function removeFilterAt(index) {
    activeFilters.splice(index, 1);
    renderActiveFilters();

    if (activeFilters.length === 0) {
        clearFilteredLayer();
        const resultsDiv = document.getElementById('filterResults');
        resultsDiv.classList.remove('active');
        resultsDiv.innerHTML = '';
    } else {
        await runFilterQuery();
    }
}

/**
 * Render the list of currently applied filters.
 */
function renderActiveFilters() {
    const container = document.getElementById('activeFilters');
    if (!container) return;

    if (activeFilters.length === 0) {
        container.innerHTML = '';
        return;
    }

    let html = '<div class="active-filters-title">Applied filters (AND)</div>';
    activeFilters.forEach((f, i) => {
        html += `
            <div class="active-filter-item">
                <code>${f.field} ${f.operator} ${f.value}</code>
                <button type="button" class="btn-close btn-close-sm"
                        aria-label="Remove filter"
                        data-filter-index="${i}"></button>
            </div>
        `;
    });
    container.innerHTML = html;

    // Wire up the remove buttons
    container.querySelectorAll('[data-filter-index]').forEach(btn => {
        btn.addEventListener('click', function() {
            removeFilterAt(parseInt(this.dataset.filterIndex, 10));
        });
    });
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
 * Clear all filters and restore the original layer
 */
function clearFilter() {
    activeFilters = [];
    renderActiveFilters();

    // Reset the form back to its default attribute/operator/value
    const fieldSelect = document.getElementById('filterField');
    fieldSelect.value = 'area';
    updateFieldControls();

    // Clear results
    const resultsDiv = document.getElementById('filterResults');
    resultsDiv.classList.remove('active');
    resultsDiv.innerHTML = '';

    // Clear filtered layer on map (this also clears the lineage layer)
    clearFilteredLayer();

    // Reset Track Lineage button if visible
    const trackLineageBtn = document.getElementById('trackLineageBtn');
    if (trackLineageBtn) {
        trackLineageBtn.classList.remove('active');
        trackLineageBtn.textContent = 'Track Lineage';
    }
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
 * Update the operator list, value control and help text for the selected
 * attribute.
 */
function updateFieldControls() {
    const fieldSelect = document.getElementById('filterField');
    const operatorSelect = document.getElementById('filterOperator');
    const valueInput = document.getElementById('filterValue');
    const valueSelect = document.getElementById('filterValueSelect');
    const fieldHelp = document.getElementById('filterFieldHelp');
    const valueHelp = document.getElementById('filterValueHelp');

    const meta = FIELD_META[fieldSelect.value];
    if (!meta) {
        operatorSelect.innerHTML = '';
        return;
    }

    // Attribute description
    fieldHelp.textContent = meta.description || '';

    // Operators
    operatorSelect.innerHTML = '';
    meta.operators.forEach(op => {
        const option = document.createElement('option');
        option.value = op.value;
        option.textContent = op.text;
        operatorSelect.appendChild(option);
    });
    if (meta.defaultOperator) {
        operatorSelect.value = meta.defaultOperator;
    }

    // Value control: dropdown for fixed option sets, free text otherwise
    if (meta.options) {
        valueSelect.innerHTML = '';
        meta.options.forEach(opt => {
            const option = document.createElement('option');
            option.value = opt.value;
            option.textContent = opt.label;
            valueSelect.appendChild(option);
        });
        valueSelect.classList.remove('d-none');
        valueInput.classList.add('d-none');
        valueInput.removeAttribute('required');
        valueSelect.setAttribute('required', 'required');
        valueHelp.textContent = '';
    } else {
        valueSelect.classList.add('d-none');
        valueSelect.removeAttribute('required');
        valueInput.classList.remove('d-none');
        valueInput.setAttribute('required', 'required');
        valueInput.placeholder = meta.placeholder || 'Enter value...';
        valueInput.value = meta.defaultValue || '';
        valueHelp.textContent = meta.valueHelp || '';
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    const filterField = document.getElementById('filterField');

    // Filter form submission (Apply Filter)
    const filterForm = document.getElementById('filterForm');
    if (filterForm) {
        filterForm.addEventListener('submit', applyFilter);
    }

    // Additional Filter button
    const additionalFilterBtn = document.getElementById('additionalFilter');
    if (additionalFilterBtn) {
        additionalFilterBtn.addEventListener('click', addAdditionalFilter);
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

    // Populate controls for the initially selected attribute, and refresh
    // them whenever the attribute changes.
    if (filterField) {
        filterField.addEventListener('change', updateFieldControls);
        updateFieldControls();
    }
});
