import '@testing-library/jest-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import * as imageOptimization from '../../utils/imageOptimization';
import { ImagePlaceholder, OptimizedImage } from '../OptimizedImage';

// Mock the image optimization utilities
jest.mock('../../utils/imageOptimization', () => ({
  generateResponsiveImageUrls: jest.fn(),
  generateOptimizedImageUrl: jest.fn(),
  globalLazyLoader: {
    observe: jest.fn(),
    unobserve: jest.fn(),
  },
}));

const mockGenerateResponsiveImageUrls = imageOptimization.generateResponsiveImageUrls as jest.Mock;
const mockGenerateOptimizedImageUrl = imageOptimization.generateOptimizedImageUrl as jest.Mock;
const mockGlobalLazyLoader = imageOptimization.globalLazyLoader as jest.Mocked<typeof imageOptimization.globalLazyLoader>;

describe('OptimizedImage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockGenerateResponsiveImageUrls.mockReturnValue({
      srcSet: 'image.jpg?w=320 320w, image.jpg?w=640 640w',
      sizes: '(max-width: 320px) 320px, 640px',
    });
    mockGenerateOptimizedImageUrl.mockReturnValue('image.jpg?w=800&q=80&f=webp');
  });

  it('should render with basic props', () => {
    render(<OptimizedImage src="test.jpg" alt="Test image" />);
    
    const img = screen.getByAltText('Test image');
    expect(img).toBeInTheDocument();
    expect(img).toHaveClass('lazy');
  });

  it('should set up lazy loading by default', () => {
    render(<OptimizedImage src="test.jpg" alt="Test image" />);
    
    expect(mockGlobalLazyLoader.observe).toHaveBeenCalled();
  });

  it('should not use lazy loading when lazy=false', () => {
    render(<OptimizedImage src="test.jpg" alt="Test image" lazy={false} />);
    
    expect(mockGlobalLazyLoader.observe).not.toHaveBeenCalled();
  });

  it('should use responsive images by default', () => {
    render(<OptimizedImage src="test.jpg" alt="Test image" lazy={false} />);
    
    expect(mockGenerateResponsiveImageUrls).toHaveBeenCalledWith('test.jpg', {});
  });

  it('should use single optimized image when responsive=false', () => {
    render(<OptimizedImage src="test.jpg" alt="Test image" lazy={false} responsive={false} />);
    
    expect(mockGenerateOptimizedImageUrl).toHaveBeenCalledWith('test.jpg', 800, {});
    expect(mockGenerateResponsiveImageUrls).not.toHaveBeenCalled();
  });

  it('should pass optimization options correctly', () => {
    const options = { quality: 90, format: 'jpeg' as const };
    render(
      <OptimizedImage 
        src="test.jpg" 
        alt="Test image" 
        lazy={false} 
        optimizationOptions={options} 
      />
    );
    
    expect(mockGenerateResponsiveImageUrls).toHaveBeenCalledWith('test.jpg', options);
  });

  it('should handle load event correctly', async () => {
    const onLoad = jest.fn();
    render(<OptimizedImage src="test.jpg" alt="Test image" onLoad={onLoad} />);
    
    const img = screen.getByAltText('Test image');
    fireEvent.load(img);
    
    await waitFor(() => {
      expect(img).toHaveClass('loaded');
      expect(onLoad).toHaveBeenCalled();
    });
  });

  it('should handle error event and fallback', async () => {
    const onError = jest.fn();
    const fallbackSrc = 'fallback.jpg';
    
    render(
      <OptimizedImage 
        src="test.jpg" 
        alt="Test image" 
        onError={onError}
        fallbackSrc={fallbackSrc}
      />
    );
    
    const img = screen.getByAltText('Test image');
    fireEvent.error(img);
    
    await waitFor(() => {
      expect(img).toHaveClass('error');
      expect(onError).toHaveBeenCalled();
      expect(img.src).toContain(fallbackSrc);
    });
  });

  it('should apply custom className', () => {
    render(<OptimizedImage src="test.jpg" alt="Test image" className="custom-class" />);
    
    const img = screen.getByAltText('Test image');
    expect(img).toHaveClass('custom-class');
  });

  it('should clean up lazy loader on unmount', () => {
    const { unmount } = render(<OptimizedImage src="test.jpg" alt="Test image" />);
    
    unmount();
    
    expect(mockGlobalLazyLoader.unobserve).toHaveBeenCalled();
  });
});

describe('ImagePlaceholder', () => {
  it('should render with default dimensions', () => {
    render(<ImagePlaceholder />);
    
    const placeholder = screen.getByTestId('image-placeholder');
    expect(placeholder).toHaveStyle({ width: '300px', height: '200px' });
  });

  it('should render with custom dimensions', () => {
    render(<ImagePlaceholder width={400} height={300} />);
    
    const placeholder = screen.getByTestId('image-placeholder');
    expect(placeholder).toHaveStyle({ width: '400px', height: '300px' });
  });

  it('should apply custom className', () => {
    render(<ImagePlaceholder className="custom-placeholder" />);
    
    const placeholder = screen.getByTestId('image-placeholder');
    expect(placeholder).toHaveClass('custom-placeholder');
  });

  it('should contain SVG icon', () => {
    render(<ImagePlaceholder />);
    
    const svg = screen.getByTestId('image-placeholder').querySelector('svg');
    expect(svg).toBeInTheDocument();
  });
});