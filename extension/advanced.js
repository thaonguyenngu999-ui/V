/**
 * S Manage - Advanced Fingerprint Spoofing
 * Handles advanced detection bypass
 */

(function() {
    'use strict';
    
    // ========== PROTOTYPE PROTECTION ==========
    // Prevent detection of modified prototypes
    
    const nativeToString = Function.prototype.toString;
    const nativeToStringStr = 'function toString() { [native code] }';
    
    // Store original functions before we modify them
    const originalFunctions = new Map();
    
    function protectFunction(obj, prop, newFunc) {
        const original = obj[prop];
        if (original) {
            originalFunctions.set(newFunc, original);
            obj[prop] = newFunc;
            
            // Make toString return native code
            newFunc.toString = function() {
                return nativeToString.call(original);
            };
        }
    }
    
    // ========== AUTOMATION FLAGS ==========
    function hideAutomationFlags() {
        // Remove automation-related properties
        const propsToHide = [
            'webdriver',
            '__webdriver_script_fn',
            '__driver_evaluate',
            '__webdriver_evaluate',
            '__selenium_evaluate',
            '__fxdriver_evaluate',
            '__driver_unwrapped',
            '__webdriver_unwrapped',
            '__selenium_unwrapped',
            '__fxdriver_unwrapped',
            '_Selenium_IDE_Recorder',
            '_selenium',
            'calledSelenium',
            '$cdc_asdjflasutopfhvcZLmcfl_',
            '$chrome_asyncScriptInfo'
        ];
        
        for (const prop of propsToHide) {
            try {
                delete window[prop];
                delete document[prop];
            } catch (e) {}
        }
        
        // Hide chrome driver
        if (window.chrome) {
            delete window.chrome.csi;
            delete window.chrome.loadTimes;
        }
        
        // Hide navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
    }
    
    // ========== IFRAME DETECTION ==========
    function protectIframe() {
        // Ensure contentWindow matches parent window properties
        const originalContentWindow = Object.getOwnPropertyDescriptor(
            HTMLIFrameElement.prototype, 'contentWindow'
        );
        
        if (originalContentWindow) {
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    const win = originalContentWindow.get.call(this);
                    if (win) {
                        // Copy parent navigator properties
                        try {
                            Object.defineProperty(win.navigator, 'webdriver', {
                                get: () => undefined
                            });
                        } catch (e) {}
                    }
                    return win;
                }
            });
        }
    }
    
    // ========== ERROR STACK TRACE ==========
    function hideStackTrace() {
        // Some fingerprinters analyze error stack traces
        const originalError = Error;
        
        window.Error = function(...args) {
            const error = new originalError(...args);
            
            // Clean stack trace
            if (error.stack) {
                error.stack = error.stack
                    .split('\n')
                    .filter(line => !line.includes('inject.js') && 
                                    !line.includes('loader.js') &&
                                    !line.includes('extension://'))
                    .join('\n');
            }
            
            return error;
        };
        
        window.Error.prototype = originalError.prototype;
        window.Error.captureStackTrace = originalError.captureStackTrace;
    }
    
    // ========== PERFORMANCE TIMING ==========
    function normalizePerformance() {
        // Normalize timing entries to look natural
        if (window.performance && window.performance.timing) {
            const timing = window.performance.timing;
            
            // Add small random delays to look natural
            const entries = [
                'domainLookupStart', 'domainLookupEnd',
                'connectStart', 'connectEnd',
                'requestStart', 'responseStart', 'responseEnd',
                'domLoading', 'domInteractive', 'domContentLoadedEventStart',
                'domContentLoadedEventEnd', 'domComplete',
                'loadEventStart', 'loadEventEnd'
            ];
        }
    }
    
    // ========== FONT FINGERPRINT ==========
    function spoofFonts() {
        // Limit available fonts to common ones
        const commonFonts = [
            'Arial', 'Verdana', 'Helvetica', 'Times New Roman',
            'Georgia', 'Courier New', 'Comic Sans MS', 'Impact',
            'Trebuchet MS', 'Arial Black', 'Tahoma'
        ];
        
        const originalFontCheck = document.fonts?.check;
        if (originalFontCheck) {
            document.fonts.check = function(font) {
                const fontFamily = font.split(' ').pop()?.replace(/['"]/g, '');
                if (fontFamily && !commonFonts.some(f => 
                    fontFamily.toLowerCase().includes(f.toLowerCase()))) {
                    return false;
                }
                return originalFontCheck.call(this, font);
            };
        }
    }
    
    // ========== SPEECH SYNTHESIS ==========
    function spoofSpeechVoices() {
        // Return consistent voice list
        if (window.speechSynthesis) {
            const originalGetVoices = window.speechSynthesis.getVoices;
            window.speechSynthesis.getVoices = function() {
                const voices = originalGetVoices.call(this);
                // Return only first 3 voices
                return voices.slice(0, 3);
            };
        }
    }
    
    // ========== GAMEPAD ==========
    function spoofGamepad() {
        // Hide gamepad API
        navigator.getGamepads = function() {
            return [];
        };
    }
    
    // ========== HARDWARE INFO ==========
    function spoofHardware() {
        // Consistent keyboard layout
        if (navigator.keyboard) {
            navigator.keyboard.getLayoutMap = async function() {
                return new Map([
                    ['KeyA', 'a'], ['KeyB', 'b'], ['KeyC', 'c']
                ]);
            };
        }
        
        // USB - return empty
        if (navigator.usb) {
            navigator.usb.getDevices = async function() {
                return [];
            };
        }
        
        // Bluetooth - return empty  
        if (navigator.bluetooth) {
            navigator.bluetooth.getDevices = async function() {
                return [];
            };
        }
        
        // HID - return empty
        if (navigator.hid) {
            navigator.hid.getDevices = async function() {
                return [];
            };
        }
    }
    
    // ========== STORAGE ESTIMATE ==========
    function spoofStorage() {
        // Return consistent storage estimate
        if (navigator.storage && navigator.storage.estimate) {
            const originalEstimate = navigator.storage.estimate.bind(navigator.storage);
            navigator.storage.estimate = async function() {
                return {
                    quota: 107374182400, // 100GB
                    usage: Math.floor(Math.random() * 10000000), // Random usage
                    usageDetails: {}
                };
            };
        }
    }
    
    // ========== CONNECTION INFO ==========
    function spoofConnection() {
        // Consistent network info
        if (navigator.connection) {
            Object.defineProperties(navigator.connection, {
                effectiveType: { get: () => '4g', configurable: true },
                downlink: { get: () => 10, configurable: true },
                rtt: { get: () => 50, configurable: true },
                saveData: { get: () => false, configurable: true }
            });
        }
    }
    
    // ========== DO NOT TRACK ==========
    function spoofDNT() {
        Object.defineProperty(navigator, 'doNotTrack', {
            get: () => null, // null = not set, which is most common
            configurable: true
        });
    }
    
    // ========== APPLY ALL ==========
    function applyAdvancedProtection() {
        try {
            hideAutomationFlags();
            protectIframe();
            hideStackTrace();
            normalizePerformance();
            spoofFonts();
            spoofSpeechVoices();
            spoofGamepad();
            spoofHardware();
            spoofStorage();
            spoofConnection();
            spoofDNT();
            
            console.log('[S Manage] Advanced protection active');
        } catch (e) {
            console.error('[S Manage] Advanced protection error:', e);
        }
    }
    
    applyAdvancedProtection();
    
})();
