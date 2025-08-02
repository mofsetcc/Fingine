/**
 * Performance monitoring utilities for tracking loading times and metrics
 */

export interface PerformanceMetrics {
  loadTime: number;
  domContentLoaded: number;
  firstContentfulPaint?: number;
  largestContentfulPaint?: number;
  cumulativeLayoutShift?: number;
  firstInputDelay?: number;
}

export class PerformanceMonitor {
  private metrics: PerformanceMetrics = {
    loadTime: 0,
    domContentLoaded: 0,
  };

  constructor() {
    this.initializeMetrics();
  }

  private initializeMetrics(): void {
    // Basic timing metrics
    window.addEventListener('load', () => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      this.metrics.loadTime = navigation.loadEventEnd - navigation.loadEventStart;
      this.metrics.domContentLoaded = navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart;
    });

    // Web Vitals metrics
    this.observeWebVitals();
  }

  private observeWebVitals(): void {
    // First Contentful Paint
    this.observePerformanceEntry('paint', (entries) => {
      const fcpEntry = entries.find(entry => entry.name === 'first-contentful-paint');
      if (fcpEntry) {
        this.metrics.firstContentfulPaint = fcpEntry.startTime;
      }
    });

    // Largest Contentful Paint
    this.observePerformanceEntry('largest-contentful-paint', (entries) => {
      const lcpEntry = entries[entries.length - 1];
      if (lcpEntry) {
        this.metrics.largestContentfulPaint = lcpEntry.startTime;
      }
    });

    // Cumulative Layout Shift
    this.observePerformanceEntry('layout-shift', (entries) => {
      let cumulativeScore = 0;
      entries.forEach((entry: any) => {
        if (!entry.hadRecentInput) {
          cumulativeScore += entry.value;
        }
      });
      this.metrics.cumulativeLayoutShift = cumulativeScore;
    });

    // First Input Delay
    this.observePerformanceEntry('first-input', (entries) => {
      const fidEntry = entries[0];
      if (fidEntry) {
        this.metrics.firstInputDelay = fidEntry.processingStart - fidEntry.startTime;
      }
    });
  }

  private observePerformanceEntry(
    entryType: string,
    callback: (entries: PerformanceEntry[]) => void
  ): void {
    try {
      const observer = new PerformanceObserver((list) => {
        callback(list.getEntries());
      });
      observer.observe({ entryTypes: [entryType] });
    } catch (error) {
      console.warn(`Performance observer for ${entryType} not supported:`, error);
    }
  }

  /**
   * Get current performance metrics
   */
  getMetrics(): PerformanceMetrics {
    return { ...this.metrics };
  }

  /**
   * Track custom timing metrics
   */
  markStart(name: string): void {
    performance.mark(`${name}-start`);
  }

  markEnd(name: string): number {
    performance.mark(`${name}-end`);
    performance.measure(name, `${name}-start`, `${name}-end`);
    
    const measure = performance.getEntriesByName(name, 'measure')[0];
    return measure.duration;
  }

  /**
   * Track resource loading times
   */
  getResourceTimings(): PerformanceResourceTiming[] {
    return performance.getEntriesByType('resource') as PerformanceResourceTiming[];
  }

  /**
   * Get bundle size information
   */
  getBundleMetrics(): { [key: string]: number } {
    const resources = this.getResourceTimings();
    const bundleMetrics: { [key: string]: number } = {};

    resources.forEach((resource) => {
      if (resource.name.includes('.js') || resource.name.includes('.css')) {
        const fileName = resource.name.split('/').pop() || 'unknown';
        bundleMetrics[fileName] = resource.transferSize || 0;
      }
    });

    return bundleMetrics;
  }

  /**
   * Report performance metrics to analytics
   */
  reportMetrics(): void {
    const metrics = this.getMetrics();
    const bundleMetrics = this.getBundleMetrics();

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.group('Performance Metrics');
      console.table(metrics);
      console.table(bundleMetrics);
      console.groupEnd();
    }

    // Send to analytics service in production
    if (process.env.NODE_ENV === 'production') {
      this.sendToAnalytics({
        ...metrics,
        bundleMetrics,
        timestamp: Date.now(),
        userAgent: navigator.userAgent,
        url: window.location.href,
      });
    }
  }

  private sendToAnalytics(data: any): void {
    // Implementation would send data to your analytics service
    // For now, we'll just log it
    console.log('Performance metrics:', data);
  }
}

// Global performance monitor instance
export const performanceMonitor = new PerformanceMonitor();

// Report metrics after page load
window.addEventListener('load', () => {
  setTimeout(() => {
    performanceMonitor.reportMetrics();
  }, 1000);
});

/**
 * Hook for tracking component render performance
 */
export function usePerformanceTracking(componentName: string) {
  React.useEffect(() => {
    performanceMonitor.markStart(`${componentName}-render`);
    
    return () => {
      const duration = performanceMonitor.markEnd(`${componentName}-render`);
      if (process.env.NODE_ENV === 'development') {
        console.log(`${componentName} render time: ${duration.toFixed(2)}ms`);
      }
    };
  }, [componentName]);
}

// Import React for the hook
import React from 'react';
