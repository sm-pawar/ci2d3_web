/**
 * CI2D3 Ice Island Explorer - Guided tour
 *
 * Walks a first-time visitor through the four things the portal can do, and
 * actually performs each one against the live app rather than just describing
 * it. Shown automatically on first visit; re-openable from the header.
 *
 * The lineage step deliberately uses an ice island whose lineage is small
 * (40 observations), so the demo stays cheap for the server.
 */

// Storage key. Bump the suffix to re-show the tour to returning visitors.
const TOUR_SEEN_KEY = 'ci2d3_tour_seen_v1';

// An ice island with a short, clean lineage: 4 ancestors, itself, 35
// descendants = 40 features. Small enough to draw instantly.
const TOUR_DEMO_INST = '20080718_161758_es_0_PUX';

let tourIndex = 0;
let tourRunning = false;

/**
 * Set the filter form to a given attribute/operator/value.
 * Drives the real controls so the tour shows exactly what a user would do.
 */
function tourSetFilter(field, operator, value) {
    const fieldSelect = document.getElementById('filterField');
    fieldSelect.value = field;
    // Let filter.js rebuild the operator list and swap the value control.
    fieldSelect.dispatchEvent(new Event('change'));

    document.getElementById('filterOperator').value = operator;

    const valueSelect = document.getElementById('filterValueSelect');
    if (!valueSelect.classList.contains('d-none')) {
        valueSelect.value = value;
    } else {
        document.getElementById('filterValue').value = value;
    }
}

/** Briefly highlight an element so the user's eye goes to it. */
function tourHighlight(selector) {
    document.querySelectorAll('.tour-highlight').forEach(
        el => el.classList.remove('tour-highlight'));
    if (!selector) return;
    const el = document.querySelector(selector);
    if (el) {
        el.classList.add('tour-highlight');
        el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
}

/** Show a short progress/result line inside the tour card. */
function tourStatus(message, kind) {
    const el = document.getElementById('tourStatus');
    if (!message) {
        el.className = 'tour-status';
        el.innerHTML = '';
        return;
    }
    el.className = `tour-status show ${kind || ''}`;
    el.innerHTML = message;
}

/** Fetch a single observation by its inst identifier. */
async function tourFetchDemoFeature() {
    const response = await fetch(`${CONFIG.apiUrl}/filter/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field: 'inst', operator: '=', value: TOUR_DEMO_INST })
    });
    if (!response.ok) throw new Error(`status ${response.status}`);
    const data = await response.json();
    if (!data.features || !data.features.length) {
        throw new Error('demo ice island not found in the database');
    }
    return data.features[0];
}

/**
 * The tour steps. `run` performs the step against the live app and returns a
 * short status line; anything it throws is reported in the card.
 */
const TOUR_STEPS = [
    {
        badge: 'Welcome',
        title: 'Ice Island Records in the CI2D3 Database',
        body: `
            <p>This portal lets you explore the Canadian Ice Island Drift,
            Deterioration and Detection database. You can:</p>
            <ul>
                <li>filter observations by attributes using the selection options,</li>
                <li>retrieve all database information<sup>*</sup> for an observation
                    by clicking an ice island polygon, and</li>
                <li>visualise an ice island's lineage &mdash; its ancestors and
                    descendants &mdash; through fracture and drift.</li>
            </ul>
            <p class="tour-note"><sup>*</sup>See the
            <a href="https://doi.org/10.22215/wirl/2018.1" target="_blank" rel="noopener">CI2D3
            Database documentation</a> for details on these fields.</p>
            <p>This short tour runs each of these for you. It takes about a minute.</p>
        `,
        highlight: null
    },
    {
        badge: 'Step 1 of 4',
        title: 'Filter by a single attribute',
        body: `
            <p>Pick an <strong>attribute</strong>, an <strong>operator</strong> and a
            <strong>value</strong>, then press <strong>Apply Filter</strong>.</p>
            <p>Here we ask for every observation larger than
            <strong>200 km&sup2;</strong> &mdash; only the biggest ice islands.</p>
        `,
        highlight: '#filterForm',
        run: async () => {
            clearFilter();
            tourSetFilter('area', '>', '200');
            await applyFilter();
            const n = currentFilteredData ? currentFilteredData.count : 0;
            return `Applied <code>area &gt; 200</code> &mdash; found <strong>${n}</strong> observations.`;
        }
    },
    {
        badge: 'Step 2 of 4',
        title: 'Stack a second filter',
        body: `
            <p>To narrow things further, change the selection and press
            <strong>Additional Filter</strong> instead of Apply Filter. Conditions
            combine with <strong>AND</strong>.</p>
            <p>We keep <code>area &gt; 200</code> and add
            <strong>Calvingloc = PG</strong>, so only large ice islands calved from
            Petermann Glacier remain. Each applied filter is listed below the form
            and can be removed individually.</p>
        `,
        highlight: '#activeFilters',
        run: async () => {
            tourSetFilter('calvingloc', '=', 'PG');
            await addAdditionalFilter();
            const n = currentFilteredData ? currentFilteredData.count : 0;
            return `Now showing <code>area &gt; 200 AND calvingloc = PG</code> &mdash; <strong>${n}</strong> observations.`;
        }
    },
    {
        badge: 'Step 3 of 4',
        title: 'Inspect an ice island',
        body: `
            <p>Click any polygon on the map to see <strong>every database field</strong>
            recorded for that observation &mdash; its area, dimensions, the satellite
            scene it came from, and its position in the lineage.</p>
            <p>We have selected one for you and opened its details on the left.</p>
        `,
        highlight: '#inspectPanel',
        run: async () => {
            clearFilter();
            const feature = await tourFetchDemoFeature();
            displayFeatureInfo(feature);
            const layer = L.geoJSON(feature);
            if (layer.getBounds().isValid()) {
                map.fitBounds(layer.getBounds(), { padding: [80, 80], maxZoom: 9 });
            }
            const p = feature.properties;
            return `Selected <code>${p.inst}</code> &mdash; ${p.area} km&sup2;, observed ${p.scenedate}.`;
        }
    },
    {
        badge: 'Step 4 of 4',
        title: 'Track its lineage',
        body: `
            <p>With an ice island selected, press <strong>Track Lineage</strong> to
            follow it through the database.</p>
            <p>Each observation links to its parent, forming a tree that spans
            fracture and drift events. The map colours them by their relationship to
            the polygon you selected:</p>
            <ul class="tour-legend">
                <li><span class="tour-swatch" style="background:#1f78b4"></span>
                    <strong>Before</strong> &mdash; ancestors it came from</li>
                <li><span class="tour-swatch" style="background:#ffd400"></span>
                    <strong>Selected</strong> &mdash; the one you picked</li>
                <li><span class="tour-swatch" style="background:#e6550d"></span>
                    <strong>After</strong> &mdash; descendants it broke into</li>
            </ul>
            <p>Numbers show the order in time, and the dashed line traces the drift.</p>
        `,
        highlight: '#trackLineageBtn',
        run: async () => {
            if (!currentInspectedFeature) {
                const feature = await tourFetchDemoFeature();
                displayFeatureInfo(feature);
            }
            await trackLineage();
            const roles = currentLineageData?.lineage?.roles;
            if (!roles) return 'Lineage drawn on the map.';
            return `Drew <strong>${currentLineageData.count}</strong> observations: ` +
                   `${roles.before} before, ${roles.after} after.`;
        }
    },
    {
        badge: 'All set',
        title: 'That is the whole tour',
        body: `
            <p>You now have the lineage of one ice island on the map. From here you can:</p>
            <ul>
                <li>click any coloured polygon to inspect it,</li>
                <li>press <strong>Clear Filter</strong> to start over, or</li>
                <li>switch the basemap from the control at the top right.</li>
            </ul>
            <p class="tour-note">You can reopen this tour any time with
            <strong>Show me how</strong> in the header.</p>
        `,
        highlight: null
    }
];

function tourRender() {
    const step = TOUR_STEPS[tourIndex];

    document.getElementById('tourBadge').textContent = step.badge;
    document.getElementById('tourTitle').textContent = step.title;
    document.getElementById('tourBody').innerHTML = step.body;
    tourStatus(null);

    // Progress dots (welcome and closing steps are not numbered)
    const dots = TOUR_STEPS.map((s, i) =>
        `<span class="tour-dot ${i === tourIndex ? 'active' : ''}"></span>`).join('');
    document.getElementById('tourDots').innerHTML = dots;

    const isFirst = tourIndex === 0;
    const isLast = tourIndex === TOUR_STEPS.length - 1;
    document.getElementById('tourBack').style.display = isFirst ? 'none' : '';
    document.getElementById('tourSkip').style.display = isLast ? 'none' : '';
    document.getElementById('tourNext').textContent =
        isFirst ? 'Start tour' : (isLast ? 'Finish' : 'Next');

    // Steps that touch the map sit to one side so the result stays visible.
    document.getElementById('tourModal').classList.toggle('tour-aside', !!step.run);
    document.getElementById('tourBackdrop').classList.toggle('dim', !step.run);

    tourHighlight(step.highlight);

    if (step.run) {
        runTourStep(step);
    }
}

async function runTourStep(step) {
    const next = document.getElementById('tourNext');
    next.disabled = true;
    tourStatus('Running&hellip;', 'running');
    try {
        const result = await step.run();
        tourStatus(result, 'done');
    } catch (err) {
        console.error('Tour step failed:', err);
        tourStatus(
            `Could not run this step: ${err.message}. ` +
            `You can still follow along manually.`, 'error');
    } finally {
        next.disabled = false;
    }
}

function openTour(startIndex) {
    tourIndex = startIndex || 0;
    tourRunning = true;
    document.getElementById('tourBackdrop').classList.add('show');
    document.getElementById('tourModal').classList.add('show');
    tourRender();
}

function closeTour() {
    tourRunning = false;
    document.getElementById('tourBackdrop').classList.remove('show', 'dim');
    document.getElementById('tourModal').classList.remove('show');
    tourHighlight(null);
    try {
        localStorage.setItem(TOUR_SEEN_KEY, '1');
    } catch (e) {
        // Private browsing / storage disabled - the tour simply shows again.
    }
}

function tourNext() {
    if (tourIndex >= TOUR_STEPS.length - 1) {
        closeTour();
        return;
    }
    tourIndex += 1;
    tourRender();
}

function tourBack() {
    if (tourIndex === 0) return;
    tourIndex -= 1;
    tourRender();
}

document.addEventListener('DOMContentLoaded', function () {
    document.getElementById('openTour').addEventListener('click', () => openTour(0));
    document.getElementById('tourNext').addEventListener('click', tourNext);
    document.getElementById('tourBack').addEventListener('click', tourBack);
    document.getElementById('tourSkip').addEventListener('click', closeTour);
    document.getElementById('tourClose').addEventListener('click', closeTour);

    document.addEventListener('keydown', e => {
        if (!tourRunning) return;
        if (e.key === 'Escape') closeTour();
        if (e.key === 'ArrowRight') tourNext();
        if (e.key === 'ArrowLeft') tourBack();
    });

    // Show automatically on a first visit, once the map has settled.
    let seen = false;
    try {
        seen = localStorage.getItem(TOUR_SEEN_KEY) === '1';
    } catch (e) {
        seen = false;
    }
    if (!seen) {
        setTimeout(() => openTour(0), 700);
    }
});
