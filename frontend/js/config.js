/**
 * CI2D3 Ice Island Explorer - Configuration
 * Dynamically detects the host for AWS EC2 or local deployment
 */

// Get the current host (works for both localhost and public IP/domain)
const getBaseUrl = () => {
    // Check if running in development (localhost)
    const hostname = window.location.hostname;
    const protocol = window.location.protocol;

    // For development
    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        return {
            geoserver: `${protocol}//${hostname}:8080`,
            api: `${protocol}//${hostname}:5000`
        };
    }

    // For production (AWS EC2 or custom domain)
    // Assumes services are on same host but different ports
    return {
        geoserver: `${protocol}//${hostname}:8080`,
        api: `${protocol}//${hostname}:5000`
    };
};

// Initialize configuration
const baseUrls = getBaseUrl();

// Export configuration
const CONFIG = {
    geoserverUrl: `${baseUrls.geoserver}/geoserver`,
    workspace: 'ci2d3',
    layer: 'iceislands',
    apiUrl: `${baseUrls.api}/api`
};

console.log('CI2D3 Configuration:', CONFIG);
