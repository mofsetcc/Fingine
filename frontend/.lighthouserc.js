module.exports = {
    ci: {
        collect: {
            // Tell Lighthouse CI where to find the built static files
            staticDistDir: './dist',
            // Alternative: Use URLs directly if server is already running
            // url: ['http://localhost:3000/'],

            // For static file testing without server
            numberOfRuns: 1, // Reduced for CI speed

            // Chrome flags optimized for CI
            settings: {
                chromeFlags: [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--headless',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=TranslateUI',
                    '--disable-extensions',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding'
                ].join(' ')
            }
        },
        assert: {
            // Relaxed performance budgets for CI environment
            assertions: {
                'categories:performance': ['warn', { minScore: 0.6 }],
                'categories:accessibility': ['warn', { minScore: 0.8 }],
                'categories:best-practices': ['warn', { minScore: 0.7 }],
                'categories:seo': ['warn', { minScore: 0.7 }],
                'categories:pwa': 'off',

                // Core Web Vitals - very lenient for CI
                'first-contentful-paint': ['warn', { maxNumericValue: 4000 }],
                'largest-contentful-paint': ['warn', { maxNumericValue: 5000 }],
                'cumulative-layout-shift': ['warn', { maxNumericValue: 0.2 }],
                'total-blocking-time': ['warn', { maxNumericValue: 1000 }]
            }
        },
        upload: {
            target: 'temporary-public-storage'
        }
    }
};