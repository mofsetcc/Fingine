/**
 * Image optimization utilities for responsive images and performance
 */

export interface ImageSizes {
  xs: number;
  sm: number;
  md: number;
  lg: number;
  xl: number;
}

export const DEFAULT_IMAGE_SIZES: ImageSizes = {
  xs: 320,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
};

export interface ImageOptimizationOptions {
  quality?: number;
  format?: 'webp' | 'jpeg' | 'png';
  sizes?: Partial<ImageSizes>;
  lazy?: boolean;
}

/**
 * Generate responsive image URLs for different screen sizes
 */
export function generateResponsiveImageUrls(
  baseUrl: string,
  options: ImageOptimizationOptions = {}
): { srcSet: string; sizes: string } {
  const { quality = 80, format = 'webp', sizes = {} } = options;
  const imageSizes = { ...DEFAULT_IMAGE_SIZES, ...sizes };

  const srcSetEntries = Object.entries(imageSizes).map(([breakpoint, width]) => {
    const optimizedUrl = `${baseUrl}?w=${width}&q=${quality}&f=${format}`;
    return `${optimizedUrl} ${width}w`;
  });

  const sizesEntries = [
    '(max-width: 320px) 320px',
    '(max-width: 640px) 640px',
    '(max-width: 768px) 768px',
    '(max-width: 1024px) 1024px',
    '1280px',
  ];

  return {
    srcSet: srcSetEntries.join(', '),
    sizes: sizesEntries.join(', '),
  };
}

/**
 * Generate optimized image URL with specific parameters
 */
export function generateOptimizedImageUrl(
  baseUrl: string,
  width: number,
  options: Omit<ImageOptimizationOptions, 'sizes'> = {}
): string {
  const { quality = 80, format = 'webp' } = options;
  return `${baseUrl}?w=${width}&q=${quality}&f=${format}`;
}

/**
 * Preload critical images for better performance
 */
export function preloadImage(src: string, as: 'image' = 'image'): void {
  const link = document.createElement('link');
  link.rel = 'preload';
  link.as = as;
  link.href = src;
  document.head.appendChild(link);
}

/**
 * Lazy load images using Intersection Observer
 */
export class LazyImageLoader {
  private observer: IntersectionObserver;
  private images: Set<HTMLImageElement> = new Set();

  constructor(options: IntersectionObserverInit = {}) {
    this.observer = new IntersectionObserver(this.handleIntersection.bind(this), {
      rootMargin: '50px 0px',
      threshold: 0.01,
      ...options,
    });
  }

  observe(img: HTMLImageElement): void {
    this.images.add(img);
    this.observer.observe(img);
  }

  unobserve(img: HTMLImageElement): void {
    this.images.delete(img);
    this.observer.unobserve(img);
  }

  private handleIntersection(entries: IntersectionObserverEntry[]): void {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        const img = entry.target as HTMLImageElement;
        const dataSrc = img.dataset.src;
        const dataSrcSet = img.dataset.srcset;

        if (dataSrc) {
          img.src = dataSrc;
          img.removeAttribute('data-src');
        }

        if (dataSrcSet) {
          img.srcset = dataSrcSet;
          img.removeAttribute('data-srcset');
        }

        img.classList.remove('lazy');
        img.classList.add('loaded');
        this.observer.unobserve(img);
        this.images.delete(img);
      }
    });
  }

  disconnect(): void {
    this.observer.disconnect();
    this.images.clear();
  }
}

// Global lazy image loader instance
export const globalLazyLoader = new LazyImageLoader();

/**
 * Convert image to WebP format if supported
 */
export function supportsWebP(): Promise<boolean> {
  return new Promise((resolve) => {
    const webP = new Image();
    webP.onload = webP.onerror = () => {
      resolve(webP.height === 2);
    };
    webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
  });
}

/**
 * Get optimal image format based on browser support
 */
export async function getOptimalImageFormat(): Promise<'webp' | 'jpeg'> {
  const webpSupported = await supportsWebP();
  return webpSupported ? 'webp' : 'jpeg';
}