/**
 * CI2D3 Ice Island Explorer - Configuration
 *
 * Works in two deployment shapes:
 *
 *  1. Behind the nginx reverse proxy (production, port 80/443).
 *     Everything is same-origin, so GeoServer and the API are reached via
 *     path prefixes on the current origin:
 *         http://<host>/geoserver   and   http://<host>/api
 *     No CORS is involved, and no port appears in any URL.
 *
 *  2. Talking straight to the containers (local development), e.g. when the
 *     page is opened on http://localhost:8080/. GeoServer and the API are
 *     then on their own ports.
 *
 * The mode is chosen from the port the page itself was served from.
 */
const getBaseUrls = () => {
    const { protocol, hostname, port, origin } = window.location;

    // No port, or the default web ports => we're behind the reverse proxy.
    const behindProxy = !port || port === '80' || port === '443';

    if (behindProxy) {
        return { geoserver: origin, api: origin };
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
