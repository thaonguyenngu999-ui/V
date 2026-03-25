/**
 * S Manage - Content Script Loader
 * Loads before page scripts to inject config
 */

(function() {
    'use strict';
    
    // Read config from URL params or storage
    function getConfigFromParams() {
        // Config có thể được pass qua URL fragment hoặc extension storage
        const params = new URLSearchParams(window.location.hash.slice(1));
        const configStr = params.get('__sm_config');
        
        if (configStr) {
            try {
                return JSON.parse(atob(configStr));
            } catch (e) {}
        }
        
        return null;
    }
    
    // Generate random but consistent fingerprint based on profile ID
    function generateFingerprint(seed) {
        // Simple hash function
        function hash(str) {
            let hash = 0;
            for (let i = 0; i < str.length; i++) {
                const char = str.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }
            return Math.abs(hash);
        }
        
        const h = hash(seed || 'default');
        
        // Screen sizes that are common
        const screenSizes = [
            [1920, 1080], [1366, 768], [1536, 864], [1440, 900],
            [1280, 720], [2560, 1440], [1680, 1050], [1600, 900]
        ];
        
        // WebGL renderers (common ones)
        const webglRenderers = [
            'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)',
            'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Direct3D11 vs_5_0 ps_5_0, D3D11)',
            'ANGLE (NVIDIA, NVIDIA GeForce RTX 2060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
            'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)',
            'ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)',
            'ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)'
        ];
        
        const webglVendors = [
            'Google Inc. (NVIDIA)',
            'Google Inc. (AMD)', 
            'Google Inc. (Intel)'
        ];
        
        const timezones = [
            ['Asia/Ho_Chi_Minh', -420],
            ['America/New_York', 300],
            ['America/Los_Angeles', 480],
            ['Europe/London', 0],
            ['Europe/Paris', -60],
            ['Asia/Tokyo', -540],
            ['Asia/Singapore', -480]
        ];
        
        const cores = [2, 4, 6, 8, 12, 16];
        const memory = [2, 4, 8, 16];
        
        // Select based on hash
        const screen = screenSizes[h % screenSizes.length];
        const renderer = webglRenderers[h % webglRenderers.length];
        const vendor = webglVendors[h % webglVendors.length];
        const tz = timezones[h % timezones.length];
        
        return {
            screenWidth: screen[0],
            screenHeight: screen[1],
            availWidth: screen[0],
            availHeight: screen[1] - 40,
            colorDepth: 24,
            pixelDepth: 24,
            
            platform: 'Win32',
            language: 'en-US',
            languages: ['en-US', 'en'],
            hardwareConcurrency: cores[h % cores.length],
            deviceMemory: memory[h % memory.length],
            maxTouchPoints: 0,
            
            timezone: tz[0],
            timezoneOffset: tz[1],
            
            webglVendor: vendor,
            webglRenderer: renderer,
            
            canvasNoise: 0.0001 + (h % 100) / 1000000,
            audioNoise: 0.0001 + (h % 50) / 1000000,
            
            battery: {
                charging: true,
                chargingTime: 0,
                dischargingTime: Infinity,
                level: 0.95 + (h % 5) / 100
            }
        };
    }
    
    // Try to get config from extension storage
    if (typeof chrome !== 'undefined' && chrome.storage) {
        chrome.storage.local.get(['profileId', 'fingerprintConfig'], (data) => {
            if (data.fingerprintConfig) {
                window.__SMANAGE_CONFIG__ = data.fingerprintConfig;
            } else if (data.profileId) {
                window.__SMANAGE_CONFIG__ = generateFingerprint(data.profileId);
            } else {
                // Generate random one
                window.__SMANAGE_CONFIG__ = generateFingerprint(Math.random().toString());
            }
        });
    } else {
        // Fallback: generate from URL or random
        const urlConfig = getConfigFromParams();
        if (urlConfig) {
            window.__SMANAGE_CONFIG__ = urlConfig;
        } else {
            window.__SMANAGE_CONFIG__ = generateFingerprint(Math.random().toString());
        }
    }
    
})();
