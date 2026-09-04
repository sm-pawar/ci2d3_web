/**
 * CI2D3 Ice Island Explorer - Configuration
 *
 * Works in three deployment shapes, all detected automatically from the URL
 * the page was served on:
 *
 *  1. Behind a reverse proxy at the site root (e.g. http://<host>/).
 *     Everything is same-origin, reached via path prefixes on the current
 *     origin:  <origin>/geoserver  and  <origin>/api
 *
 *  2. Behind a reverse proxy under a SUB-PATH, e.g. the production WIRL host:
 *         https://wirl.carleton.ca/ci2d3_v1_map/
 *     GeoServer and the API are then reached relative to that sub-path:
 *         <origin>/research/.../ci2d3_v1_map/geoserver
 *         <origin>/research/.../ci2d3_v1_map/api
 *     The frontend nginx forwards those two prefixes on to the (IP-restricted)
 *     backend server, so the browser only ever talks to this one origin and no
 *     CORS is involved.
 *
 *  3. Talking straight to the containers (local development), e.g. when the
 *     page is opened on http://localhost:8080/. GeoServer and the API are then
 *     on their own ports (8080 / 5000).
 *
 * Modes 1 and 2 are the same code path: GeoServer and the API always live
 * directly under the directory this page is served from, so we derive that
 * directory from window.location and everything follows. A trailing slash on
 * the page URL is assumed (the reverse proxy redirects to add one); index.html
 * or any trailing filename is stripped defensively just in case.
 */
const getBaseUrls = () => {
    const { protocol, hostname, port, origin, pathname } = window.location;

    // No port, or the default web ports => we're behind the reverse proxy
    // (mode 1 or 2). Otherwise we're hitting a container port directly (mode 3).
    const behindProxy = !port || port === '80' || port === '443';

    if (behindProxy) {
        // Directory the page is served from, WITH a trailing slash.
        // "/research/.../ci2d3_v1_map/"        -> unchanged
        // "/research/.../ci2d3_v1_map/index.html" -> ".../ci2d3_v1_map/"
        // "/"                                  -> "/"
        const basePath = pathname.replace(/[^/]*$/, '');

        // origin already carries protocol + host (+ non-default port, but here
        // there is none). Strip the single trailing slash so the join below
        // produces exactly one.
        const base = `${origin}${basePath}`.replace(/\/$/, '');

        return { geoserver: base, api: base };
    }

    // Direct container access (development).
    return {
        geoserver: `${protocol}//${hostname}:8080`,
        api: `${protocol}//${hostname}:5000`
    };
};

const baseUrls = getBaseUrls();

const CONFIG = {
    geoserverUrl: `${baseUrls.geoserver}/geoserver`,
    workspace: 'ci2d3',
    layer: 'iceislands',
    apiUrl: `${baseUrls.api}/api`
};

console.log('CI2D3 Configuration:', CONFIG);
