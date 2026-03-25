/**
 * S Manage - Background Service Worker
 * Handles extension lifecycle and messaging
 */

// Extension installed
chrome.runtime.onInstalled.addListener(() => {
    console.log('[S Manage] Extension installed');
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.type === 'getConfig') {
        // Return fingerprint config
        chrome.storage.local.get('fingerprintConfig', (data) => {
            sendResponse(data.fingerprintConfig || {});
        });
        return true; // Keep channel open for async response
    }
    
    if (message.type === 'log') {
        console.log('[S Manage Tab]', message.data);
    }
});

// Modify request headers to remove fingerprinting vectors
chrome.webRequest?.onBeforeSendHeaders?.addListener(
    (details) => {
        const headers = details.requestHeaders;
        
        // Remove/modify headers that can be used for fingerprinting
        const headersToModify = {
            // Remove client hints that leak info
            'sec-ch-ua-platform-version': null,
            'sec-ch-ua-bitness': null,
            'sec-ch-ua-model': null,
            'sec-ch-ua-full-version-list': null
        };
        
        for (let i = headers.length - 1; i >= 0; i--) {
            const name = headers[i].name.toLowerCase();
            if (headersToModify.hasOwnProperty(name) && headersToModify[name] === null) {
                headers.splice(i, 1);
            }
        }
        
        return { requestHeaders: headers };
    },
    { urls: ['<all_urls>'] },
    ['blocking', 'requestHeaders']
);

// Monitor for fingerprinting attempts
chrome.webNavigation?.onCompleted?.addListener((details) => {
    if (details.frameId === 0) {
        // Main frame loaded
        console.log('[S Manage] Page loaded:', details.url);
    }
});
