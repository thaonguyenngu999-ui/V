/**
 * S Manage - Fingerprint Injection Script
 * Inject vào trang web để thay đổi fingerprint
 */

(function() {
    'use strict';
    
    // ========== CONFIG ==========
    // Đọc config từ window hoặc dùng default
    const config = window.__SMANAGE_CONFIG__ || {
        // Screen
        screenWidth: 1920,
        screenHeight: 1080,
        availWidth: 1920,
        availHeight: 1040,
        colorDepth: 24,
        pixelDepth: 24,
        
        // Navigator
        platform: 'Win32',
        language: 'en-US',
        languages: ['en-US', 'en'],
        hardwareConcurrency: 8,
        deviceMemory: 8,
        maxTouchPoints: 0,
        
        // Timezone
        timezone: 'Asia/Ho_Chi_Minh',
        timezoneOffset: -420, // UTC+7
        
        // WebGL
        webglVendor: 'Google Inc. (NVIDIA)',
        webglRenderer: 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)',
        
        // Canvas noise
        canvasNoise: 0.0001,
        
        // Audio noise  
        audioNoise: 0.0001,
        
        // Battery
        battery: {
            charging: true,
            chargingTime: 0,
            dischargingTime: Infinity,
            level: 1.0
        }
    };
    
    // ========== UTILS ==========
    const originalDefineProperty = Object.defineProperty;
    
    function spoofValue(obj, prop, value) {
        try {
            originalDefineProperty(obj, prop, {
                get: () => value,
                configurable: true
            });
        } catch (e) {}
    }
    
    function spoofMethod(obj, method, fn) {
        try {
            obj[method] = fn;
        } catch (e) {}
    }
    
    // ========== SCREEN ==========
    function spoofScreen() {
        const screenProps = {
            width: config.screenWidth,
            height: config.screenHeight,
            availWidth: config.availWidth,
            availHeight: config.availHeight,
            colorDepth: config.colorDepth,
            pixelDepth: config.pixelDepth
        };
        
        for (const [prop, value] of Object.entries(screenProps)) {
            spoofValue(screen, prop, value);
        }
        
        // Window dimensions
        spoofValue(window, 'innerWidth', config.screenWidth);
        spoofValue(window, 'innerHeight', config.screenHeight - 80);
        spoofValue(window, 'outerWidth', config.screenWidth);
        spoofValue(window, 'outerHeight', config.screenHeight);
    }
    
    // ========== NAVIGATOR ==========
    function spoofNavigator() {
        const nav = window.navigator;
        
        spoofValue(nav, 'platform', config.platform);
        spoofValue(nav, 'language', config.language);
        spoofValue(nav, 'languages', Object.freeze([...config.languages]));
        spoofValue(nav, 'hardwareConcurrency', config.hardwareConcurrency);
        spoofValue(nav, 'deviceMemory', config.deviceMemory);
        spoofValue(nav, 'maxTouchPoints', config.maxTouchPoints);
        
        // Plugins - return empty but realistic
        const pluginArray = {
            length: 5,
            item: () => null,
            namedItem: () => null,
            refresh: () => {},
            [Symbol.iterator]: function* () {}
        };
        spoofValue(nav, 'plugins', pluginArray);
        
        // Disable WebDriver detection
        spoofValue(nav, 'webdriver', false);
        
        // User agent data
        if (nav.userAgentData) {
            const brands = [
                { brand: "Chromium", version: "120" },
                { brand: "Google Chrome", version: "120" },
                { brand: "Not_A Brand", version: "8" }
            ];
            
            spoofValue(nav.userAgentData, 'brands', brands);
            spoofValue(nav.userAgentData, 'mobile', false);
            spoofValue(nav.userAgentData, 'platform', 'Windows');
        }
    }
    
    // ========== TIMEZONE ==========
    function spoofTimezone() {
        // Override Date.prototype.getTimezoneOffset
        const originalGetTimezoneOffset = Date.prototype.getTimezoneOffset;
        Date.prototype.getTimezoneOffset = function() {
            return config.timezoneOffset;
        };
        
        // Override Intl.DateTimeFormat
        const originalDateTimeFormat = Intl.DateTimeFormat;
        Intl.DateTimeFormat = function(locales, options) {
            options = options || {};
            options.timeZone = options.timeZone || config.timezone;
            return new originalDateTimeFormat(locales, options);
        };
        Intl.DateTimeFormat.prototype = originalDateTimeFormat.prototype;
        
        // resolvedOptions
        const originalResolvedOptions = Intl.DateTimeFormat.prototype.resolvedOptions;
        Intl.DateTimeFormat.prototype.resolvedOptions = function() {
            const result = originalResolvedOptions.call(this);
            result.timeZone = config.timezone;
            return result;
        };
    }
    
    // ========== WEBGL ==========
    function spoofWebGL() {
        const getParameterProxyHandler = {
            apply: function(target, thisArg, args) {
                const param = args[0];
                
                // UNMASKED_VENDOR_WEBGL
                if (param === 37445) {
                    return config.webglVendor;
                }
                // UNMASKED_RENDERER_WEBGL  
                if (param === 37446) {
                    return config.webglRenderer;
                }
                
                return Reflect.apply(target, thisArg, args);
            }
        };
        
        // WebGL
        const getContext = HTMLCanvasElement.prototype.getContext;
        HTMLCanvasElement.prototype.getContext = function(type, attributes) {
            const context = getContext.call(this, type, attributes);
            
            if (context && (type === 'webgl' || type === 'webgl2' || type === 'experimental-webgl')) {
                // Proxy getParameter
                if (context.getParameter) {
                    context.getParameter = new Proxy(context.getParameter, getParameterProxyHandler);
                }
                
                // Also hook getExtension for debug info
                const originalGetExtension = context.getExtension.bind(context);
                context.getExtension = function(name) {
                    const ext = originalGetExtension(name);
                    if (ext && name === 'WEBGL_debug_renderer_info') {
                        return ext;
                    }
                    return ext;
                };
            }
            
            return context;
        };
    }
    
    // ========== CANVAS ==========
    function spoofCanvas() {
        // Add noise to canvas fingerprint
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type, quality) {
            // Only add noise for fingerprinting attempts (small canvases)
            if (this.width < 500 && this.height < 100) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    const data = imageData.data;
                    
                    // Add subtle noise
                    for (let i = 0; i < data.length; i += 4) {
                        // Only modify some pixels
                        if (Math.random() < config.canvasNoise) {
                            data[i] = data[i] ^ 1;     // R
                            data[i+1] = data[i+1] ^ 1; // G
                            data[i+2] = data[i+2] ^ 1; // B
                        }
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
            }
            
            return originalToDataURL.call(this, type, quality);
        };
        
        // Also toBlob
        const originalToBlob = HTMLCanvasElement.prototype.toBlob;
        HTMLCanvasElement.prototype.toBlob = function(callback, type, quality) {
            if (this.width < 500 && this.height < 100) {
                const ctx = this.getContext('2d');
                if (ctx) {
                    const imageData = ctx.getImageData(0, 0, this.width, this.height);
                    const data = imageData.data;
                    
                    for (let i = 0; i < data.length; i += 4) {
                        if (Math.random() < config.canvasNoise) {
                            data[i] = data[i] ^ 1;
                        }
                    }
                    ctx.putImageData(imageData, 0, 0);
                }
            }
            
            return originalToBlob.call(this, callback, type, quality);
        };
    }
    
    // ========== AUDIO ==========
    function spoofAudio() {
        // Add noise to AudioContext fingerprint
        const originalCreateAnalyser = AudioContext.prototype.createAnalyser;
        AudioContext.prototype.createAnalyser = function() {
            const analyser = originalCreateAnalyser.call(this);
            
            const originalGetFloatFrequencyData = analyser.getFloatFrequencyData.bind(analyser);
            analyser.getFloatFrequencyData = function(array) {
                originalGetFloatFrequencyData(array);
                // Add noise
                for (let i = 0; i < array.length; i++) {
                    array[i] += (Math.random() - 0.5) * config.audioNoise;
                }
            };
            
            return analyser;
        };
        
        // Oscillator node fingerprint
        const originalCreateOscillator = AudioContext.prototype.createOscillator;
        AudioContext.prototype.createOscillator = function() {
            const oscillator = originalCreateOscillator.call(this);
            return oscillator;
        };
    }
    
    // ========== CLIENT RECTS ==========
    function spoofClientRects() {
        // Add tiny noise to getBoundingClientRect for fingerprint detection
        const originalGetBoundingClientRect = Element.prototype.getBoundingClientRect;
        Element.prototype.getBoundingClientRect = function() {
            const rect = originalGetBoundingClientRect.call(this);
            
            // Only add noise for likely fingerprinting elements
            if (this.tagName === 'SPAN' || this.classList.contains('fp-test')) {
                const noise = 0.00001;
                return new DOMRect(
                    rect.x + Math.random() * noise,
                    rect.y + Math.random() * noise,
                    rect.width + Math.random() * noise,
                    rect.height + Math.random() * noise
                );
            }
            
            return rect;
        };
    }
    
    // ========== BATTERY ==========
    function spoofBattery() {
        // Override getBattery
        if (navigator.getBattery) {
            navigator.getBattery = async function() {
                return {
                    charging: config.battery.charging,
                    chargingTime: config.battery.chargingTime,
                    dischargingTime: config.battery.dischargingTime,
                    level: config.battery.level,
                    addEventListener: () => {},
                    removeEventListener: () => {}
                };
            };
        }
    }
    
    // ========== WEBRTC ==========
    function spoofWebRTC() {
        // Disable WebRTC IP leak
        const originalRTCPeerConnection = window.RTCPeerConnection;
        
        if (originalRTCPeerConnection) {
            window.RTCPeerConnection = function(config) {
                // Block local IP candidates
                const pc = new originalRTCPeerConnection(config);
                
                const originalAddEventListener = pc.addEventListener.bind(pc);
                pc.addEventListener = function(type, listener, options) {
                    if (type === 'icecandidate') {
                        const wrappedListener = function(event) {
                            if (event.candidate && event.candidate.candidate) {
                                // Filter out local IP addresses
                                const candidate = event.candidate.candidate;
                                if (candidate.includes('host') || 
                                    candidate.match(/(\d{1,3}\.){3}\d{1,3}/)) {
                                    // Block local candidates
                                    return;
                                }
                            }
                            listener(event);
                        };
                        return originalAddEventListener(type, wrappedListener, options);
                    }
                    return originalAddEventListener(type, listener, options);
                };
                
                return pc;
            };
            window.RTCPeerConnection.prototype = originalRTCPeerConnection.prototype;
        }
    }
    
    // ========== PERMISSIONS ==========
    function spoofPermissions() {
        // Override permissions.query to appear normal
        if (navigator.permissions && navigator.permissions.query) {
            const originalQuery = navigator.permissions.query.bind(navigator.permissions);
            navigator.permissions.query = async function(descriptor) {
                // Return granted for common permissions to appear normal
                const normalPermissions = ['notifications', 'geolocation', 'camera', 'microphone'];
                
                if (normalPermissions.includes(descriptor.name)) {
                    return {
                        name: descriptor.name,
                        state: 'prompt',
                        addEventListener: () => {},
                        removeEventListener: () => {}
                    };
                }
                
                return originalQuery(descriptor);
            };
        }
    }
    
    // ========== MEDIA DEVICES ==========
    function spoofMediaDevices() {
        // Return consistent device list
        if (navigator.mediaDevices && navigator.mediaDevices.enumerateDevices) {
            navigator.mediaDevices.enumerateDevices = async function() {
                return [
                    { deviceId: 'default', groupId: 'default', kind: 'audioinput', label: '' },
                    { deviceId: 'default', groupId: 'default', kind: 'audiooutput', label: '' },
                    { deviceId: 'default', groupId: 'default', kind: 'videoinput', label: '' }
                ];
            };
        }
    }
    
    // ========== APPLY ALL ==========
    function applyAllSpoofs() {
        try {
            spoofScreen();
            spoofNavigator();
            spoofTimezone();
            spoofWebGL();
            spoofCanvas();
            spoofAudio();
            spoofClientRects();
            spoofBattery();
            spoofWebRTC();
            spoofPermissions();
            spoofMediaDevices();
            
            console.log('[S Manage] Fingerprint protection active');
        } catch (e) {
            console.error('[S Manage] Error applying spoofs:', e);
        }
    }
    
    // Apply immediately
    applyAllSpoofs();
    
})();
