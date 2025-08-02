import {
    DEFAULT_IMAGE_SIZES,
    generateOptimizedImageUrl,
    generateResponsiveImageUrls,
    getOptimalImageFormat,
    LazyImageLoader,
    supportsWebP,
} from '../imageOptimization';

// Mock IntersectionObserver
const mockIntersectionObserver = jest.fn();
mockIntersectionObserver.mockReturnValue({
  observe: jest.fn(),
  unobserve: jest.fn(),
  disconnect: jest.fn(),
});
window.IntersectionObserver = mockIntersectionObserver;

describe('Image Optimization Utils', () => {
  describe('generateResponsiveImageUrls', () => {
    it('should generate correct srcSet and sizes for default breakpoints', () => {
      const baseUrl = 'https://example.com/image.jpg';
      const result = generateResponsiveImageUrls(baseUrl);

      expect(result.srcSet).toContain('https://example.com/image.jpg?w=320&q=80&f=webp 320w');
      expect(result.srcSet).toContain('https://example.com/image.jpg?w=640&q=80&f=webp 640w');
      expect(result.srcSet).toContain('https://example.com/image.jpg?w=768&q=80&f=webp 768w');
      expect(result.srcSet).toContain('https://example.com/image.jpg?w=1024&q=80&f=webp 1024w');
      expect(result.srcSet).toContain('https://example.com/image.jpg?w=1280&q=80&f=webp 1280w');

      expect(result.sizes).toBe(
        '(max-width: 320px) 320px, (max-width: 640px) 640px, (max-width: 768px) 768px, (max-width: 1024px) 1024px, 1280px'
      );
    });

    it('should use custom quality and format options', () => {
      const baseUrl = 'https://example.com/image.jpg';
      const options = { quality: 90, format: 'jpeg' as const };
      const result = generateResponsiveImageUrls(baseUrl, options);

      expect(result.srcSet).toContain('q=90');
      expect(result.srcSet).toContain('f=jpeg');
    });

    it('should use custom sizes', () => {
      const baseUrl = 'https://example.com/image.jpg';
      const options = { sizes: { sm: 480, md: 960 } };
      const result = generateResponsiveImageUrls(baseUrl, options);

      expect(result.srcSet).toContain('w=480');
      expect(result.srcSet).toContain('w=960');
      // Should still include default sizes not overridden
      expect(result.srcSet).toContain('w=320');
      expect(result.srcSet).toContain('w=1024');
      expect(result.srcSet).toContain('w=1280');
    });
  });

  describe('generateOptimizedImageUrl', () => {
    it('should generate correct optimized URL with default options', () => {
      const baseUrl = 'https://example.com/image.jpg';
      const width = 800;
      const result = generateOptimizedImageUrl(baseUrl, width);

      expect(result).toBe('https://example.com/image.jpg?w=800&q=80&f=webp');
    });

    it('should use custom quality and format', () => {
      const baseUrl = 'https://example.com/image.jpg';
      const width = 800;
      const options = { quality: 95, format: 'png' as const };
      const result = generateOptimizedImageUrl(baseUrl, width, options);

      expect(result).toBe('https://example.com/image.jpg?w=800&q=95&f=png');
    });
  });

  describe('LazyImageLoader', () => {
    let loader: LazyImageLoader;
    let mockImg: HTMLImageElement;

    beforeEach(() => {
      loader = new LazyImageLoader();
      mockImg = document.createElement('img');
      mockImg.dataset.src = 'https://example.com/image.jpg';
      mockImg.dataset.srcset = 'https://example.com/image.jpg?w=320 320w';
    });

    afterEach(() => {
      loader.disconnect();
    });

    it('should observe images', () => {
      const observeSpy = jest.spyOn(loader['observer'], 'observe');
      loader.observe(mockImg);

      expect(observeSpy).toHaveBeenCalledWith(mockImg);
    });

    it('should unobserve images', () => {
      const unobserveSpy = jest.spyOn(loader['observer'], 'unobserve');
      loader.observe(mockImg);
      loader.unobserve(mockImg);

      expect(unobserveSpy).toHaveBeenCalledWith(mockImg);
    });

    it('should handle intersection correctly', () => {
      const mockEntries = [
        {
          target: mockImg,
          isIntersecting: true,
        } as IntersectionObserverEntry,
      ];

      loader['handleIntersection'](mockEntries);

      expect(mockImg.src).toBe('https://example.com/image.jpg');
      expect(mockImg.srcset).toBe('https://example.com/image.jpg?w=320 320w');
      expect(mockImg.dataset.src).toBeUndefined();
      expect(mockImg.dataset.srcset).toBeUndefined();
      expect(mockImg.classList.contains('lazy')).toBe(false);
      expect(mockImg.classList.contains('loaded')).toBe(true);
    });
  });

  describe('supportsWebP', () => {
    it('should return a promise', () => {
      const result = supportsWebP();
      expect(result).toBeInstanceOf(Promise);
    });

    it('should resolve to boolean', async () => {
      // Mock Image constructor for WebP test
      const mockImage = {
        onload: null as any,
        onerror: null as any,
        height: 2, // Simulate WebP support
        src: '',
      };
      
      global.Image = jest.fn().mockImplementation(() => mockImage);
      
      const resultPromise = supportsWebP();
      
      // Simulate image load
      setTimeout(() => {
        if (mockImage.onload) mockImage.onload();
      }, 0);
      
      const result = await resultPromise;
      expect(typeof result).toBe('boolean');
    }, 1000);
  });

  describe('getOptimalImageFormat', () => {
    it('should return webp when supported', async () => {
      // Mock Image for WebP support
      const mockImage = {
        onload: null as any,
        onerror: null as any,
        height: 2,
        src: '',
      };
      
      global.Image = jest.fn().mockImplementation(() => mockImage);
      
      const resultPromise = getOptimalImageFormat();
      
      // Simulate WebP support
      setTimeout(() => {
        if (mockImage.onload) mockImage.onload();
      }, 0);
      
      const result = await resultPromise;
      expect(result).toBe('webp');
    }, 1000);

    it('should return jpeg when webp not supported', async () => {
      // Mock Image for no WebP support
      const mockImage = {
        onload: null as any,
        onerror: null as any,
        height: 0, // No WebP support
        src: '',
      };
      
      global.Image = jest.fn().mockImplementation(() => mockImage);
      
      const resultPromise = getOptimalImageFormat();
      
      // Simulate no WebP support
      setTimeout(() => {
        if (mockImage.onload) mockImage.onload();
      }, 0);
      
      const result = await resultPromise;
      expect(result).toBe('jpeg');
    }, 1000);
  });

  describe('DEFAULT_IMAGE_SIZES', () => {
    it('should have correct default breakpoints', () => {
      expect(DEFAULT_IMAGE_SIZES).toEqual({
        xs: 320,
        sm: 640,
        md: 768,
        lg: 1024,
        xl: 1280,
      });
    });
  });
});