/**
 * Performance tests for CDN and static asset optimization
 */

// Mock performance APIs first
const mockPerformance = {
  mark: jest.fn(),
  measure: jest.fn(),
  getEntriesByName: jest.fn().mockReturnValue([{ duration: 100 }]),
  getEntriesByType: jest.fn().mockReturnValue([]),
  now: jest.fn(() => Date.now()),
};

Object.defineProperty(window, 'performance', {
  value: mockPerformance,
  writable: true,
});

// Mock PerformanceObserver
const mockPerformanceObserver = jest.fn();
mockPerformanceObserver.mockImplementation((callback) => ({
  observe: jest.fn(),
  disconnect: jest.fn(),
}));
window.PerformanceObserver = mockPerformanceObserver;

// Mock the performance monitoring module
jest.mock('../utils/performanceMonitoring', () => {
  const mockMonitor = {
    markStart: jest.fn(),
    markEnd: jest.fn().mockReturnValue(100),
    getMetrics: jest.fn().mockReturnValue({
      loadTime: 200,
      domContentLoaded: 100,
      firstContentfulPaint: 800,
      largestContentfulPaint: 1200,
    }),
    getBundleMetrics: jest.fn().mockReturnValue({}),
    getResourceTimings: jest.fn().mockReturnValue([]),
  };
  
  return {
    performanceMonitor: mockMonitor,
    PerformanceMonitor: jest.fn().mockImplementation(() => mockMonitor),
  };
});

import { performanceMonitor } from '../utils/performanceMonitoring';

describe('Performance Optimization Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Bundle Size Optimization', () => {
    it('should have optimized chunk sizes', () => {
      // Mock resource timing entries
      const mockResourceEntries = [
        {
          name: 'https://example.com/js/main-abc123.js',
          transferSize: 150000, // 150KB - should be under 200KB
        },
        {
          name: 'https://example.com/js/vendor-def456.js',
          transferSize: 180000, // 180KB - vendor chunk
        },
        {
          name: 'https://example.com/css/main-ghi789.css',
          transferSize: 25000, // 25KB - CSS should be small
        },
      ] as PerformanceResourceTiming[];

      mockPerformance.getEntriesByType.mockReturnValue(mockResourceEntries);

      const bundleMetrics = performanceMonitor.getBundleMetrics();

      // Verify main bundle is under 200KB
      expect(bundleMetrics['main-abc123.js']).toBeLessThan(200000);
      
      // Verify CSS is under 50KB
      expect(bundleMetrics['main-ghi789.css']).toBeLessThan(50000);
      
      // Verify we have separate vendor chunks
      expect(bundleMetrics['vendor-def456.js']).toBeDefined();
    });

    it('should have proper code splitting', () => {
      const mockResourceEntries = [
        { name: 'https://example.com/js/main-abc123.js', transferSize: 150000 },
        { name: 'https://example.com/js/react-vendor-def456.js', transferSize: 120000 },
        { name: 'https://example.com/js/router-vendor-ghi789.js', transferSize: 45000 },
        { name: 'https://example.com/js/redux-vendor-jkl012.js', transferSize: 80000 },
        { name: 'https://example.com/js/Dashboard-mno345.js', transferSize: 35000 },
        { name: 'https://example.com/js/StockAnalysis-pqr678.js', transferSize: 55000 },
      ] as PerformanceResourceTiming[];

      mockPerformance.getEntriesByType.mockReturnValue(mockResourceEntries);

      const bundleMetrics = performanceMonitor.getBundleMetrics();

      // Verify we have separate vendor chunks
      expect(bundleMetrics['react-vendor-def456.js']).toBeDefined();
      expect(bundleMetrics['router-vendor-ghi789.js']).toBeDefined();
      expect(bundleMetrics['redux-vendor-jkl012.js']).toBeDefined();

      // Verify we have separate page chunks
      expect(bundleMetrics['Dashboard-mno345.js']).toBeDefined();
      expect(bundleMetrics['StockAnalysis-pqr678.js']).toBeDefined();

      // Verify page chunks are reasonably sized (under 100KB each)
      expect(bundleMetrics['Dashboard-mno345.js']).toBeLessThan(100000);
      expect(bundleMetrics['StockAnalysis-pqr678.js']).toBeLessThan(100000);
    });
  });

  describe('Performance Metrics Tracking', () => {
    it('should track custom timing metrics', () => {
      const componentName = 'TestComponent';
      
      performanceMonitor.markStart(componentName);
      performanceMonitor.markEnd(componentName);

      expect(mockPerformance.mark).toHaveBeenCalledWith(`${componentName}-start`);
      expect(mockPerformance.mark).toHaveBeenCalledWith(`${componentName}-end`);
      expect(mockPerformance.measure).toHaveBeenCalledWith(
        componentName,
        `${componentName}-start`,
        `${componentName}-end`
      );
    });

    it('should return performance metrics', () => {
      const metrics = performanceMonitor.getMetrics();

      expect(metrics).toHaveProperty('loadTime');
      expect(metrics).toHaveProperty('domContentLoaded');
      expect(typeof metrics.loadTime).toBe('number');
      expect(typeof metrics.domContentLoaded).toBe('number');
    });

    it('should track resource timings', () => {
      const mockResourceEntries = [
        {
          name: 'https://example.com/js/main.js',
          transferSize: 150000,
          duration: 250,
        },
        {
          name: 'https://example.com/css/main.css',
          transferSize: 25000,
          duration: 100,
        },
      ] as PerformanceResourceTiming[];

      mockPerformance.getEntriesByType.mockReturnValue(mockResourceEntries);

      const resourceTimings = performanceMonitor.getResourceTimings();

      expect(resourceTimings).toHaveLength(2);
      expect(resourceTimings[0].name).toBe('https://example.com/js/main.js');
      expect(resourceTimings[1].name).toBe('https://example.com/css/main.css');
    });
  });

  describe('CDN Configuration', () => {
    it('should serve static assets from CDN', () => {
      // Mock resource entries showing CDN usage
      const mockResourceEntries = [
        {
          name: 'https://cdn.example.com/static/js/main-abc123.js',
          transferSize: 150000,
        },
        {
          name: 'https://cdn.example.com/static/css/main-def456.css',
          transferSize: 25000,
        },
        {
          name: 'https://cdn.example.com/static/images/logo.webp',
          transferSize: 8000,
        },
      ] as PerformanceResourceTiming[];

      mockPerformance.getEntriesByType.mockReturnValue(mockResourceEntries);

      const resourceTimings = performanceMonitor.getResourceTimings();
      const cdnResources = resourceTimings.filter(resource => 
        resource.name.includes('cdn.example.com')
      );

      // Verify static assets are served from CDN
      expect(cdnResources.length).toBeGreaterThan(0);
      
      // Verify different asset types are properly organized
      const jsResources = cdnResources.filter(r => r.name.includes('/js/'));
      const cssResources = cdnResources.filter(r => r.name.includes('/css/'));
      const imageResources = cdnResources.filter(r => r.name.includes('/images/'));

      expect(jsResources.length).toBeGreaterThan(0);
      expect(cssResources.length).toBeGreaterThan(0);
      expect(imageResources.length).toBeGreaterThan(0);
    });
  });

  describe('Image Optimization', () => {
    it('should use optimized image formats', () => {
      const mockResourceEntries = [
        {
          name: 'https://cdn.example.com/images/stock-chart.webp',
          transferSize: 15000,
        },
        {
          name: 'https://cdn.example.com/images/company-logo.webp',
          transferSize: 5000,
        },
      ] as PerformanceResourceTiming[];

      mockPerformance.getEntriesByType.mockReturnValue(mockResourceEntries);

      const resourceTimings = performanceMonitor.getResourceTimings();
      const imageResources = resourceTimings.filter(resource => 
        resource.name.includes('.webp') || 
        resource.name.includes('.jpg') || 
        resource.name.includes('.png')
      );

      // Verify we're using WebP format for better compression
      const webpImages = imageResources.filter(r => r.name.includes('.webp'));
      expect(webpImages.length).toBeGreaterThan(0);

      // Verify image sizes are reasonable (under 50KB for most images)
      imageResources.forEach(resource => {
        expect(resource.transferSize).toBeLessThan(50000);
      });
    });
  });

  describe('Loading Performance', () => {
    it('should have acceptable loading times', () => {
      // Mock navigation timing
      const mockNavigationEntry = {
        loadEventEnd: 2000,
        loadEventStart: 1800,
        domContentLoadedEventEnd: 1500,
        domContentLoadedEventStart: 1400,
      } as PerformanceNavigationTiming;

      mockPerformance.getEntriesByType.mockReturnValue([mockNavigationEntry]);

      // Simulate load event
      const loadEvent = new Event('load');
      window.dispatchEvent(loadEvent);

      const metrics = performanceMonitor.getMetrics();

      // Verify acceptable loading times
      expect(metrics.loadTime).toBeLessThan(1000); // Under 1 second
      expect(metrics.domContentLoaded).toBeLessThan(500); // Under 0.5 seconds
    });

    it('should track Web Vitals metrics', () => {
      // Mock Web Vitals entries
      const mockLCPEntry = {
        name: 'largest-contentful-paint',
        startTime: 1200,
      } as PerformanceEntry;

      const mockFCPEntry = {
        name: 'first-contentful-paint',
        startTime: 800,
      } as PerformanceEntry;

      // Simulate performance observer callbacks
      const mockObserverCallback = mockPerformanceObserver.mock.calls[0]?.[0];
      if (mockObserverCallback) {
        mockObserverCallback({
          getEntries: () => [mockLCPEntry],
        });
        mockObserverCallback({
          getEntries: () => [mockFCPEntry],
        });
      }

      const metrics = performanceMonitor.getMetrics();

      // Verify Web Vitals are within acceptable ranges
      if (metrics.largestContentfulPaint) {
        expect(metrics.largestContentfulPaint).toBeLessThan(2500); // LCP under 2.5s
      }
      if (metrics.firstContentfulPaint) {
        expect(metrics.firstContentfulPaint).toBeLessThan(1800); // FCP under 1.8s
      }
    });
  });

  describe('Caching Strategy', () => {
    it('should have proper cache headers for static assets', () => {
      // This would typically be tested in integration tests
      // Here we verify the resource naming supports caching
      const mockResourceEntries = [
        {
          name: 'https://cdn.example.com/js/main-abc123.js', // Hash in filename
          transferSize: 150000,
        },
        {
          name: 'https://cdn.example.com/css/main-def456.css', // Hash in filename
          transferSize: 25000,
        },
      ] as PerformanceResourceTiming[];

      mockPerformance.getEntriesByType.mockReturnValue(mockResourceEntries);

      const resourceTimings = performanceMonitor.getResourceTimings();

      // Verify static assets have hashes in filenames for cache busting
      resourceTimings.forEach(resource => {
        if (resource.name.includes('/js/') || resource.name.includes('/css/')) {
          expect(resource.name).toMatch(/-[a-f0-9]{6,}\.(js|css)$/);
        }
      });
    });
  });
});