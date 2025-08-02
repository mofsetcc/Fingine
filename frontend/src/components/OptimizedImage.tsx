import React, { useEffect, useRef, useState } from 'react';
import {
    generateOptimizedImageUrl,
    generateResponsiveImageUrls,
    globalLazyLoader,
    ImageOptimizationOptions,
} from '../utils/imageOptimization';

interface OptimizedImageProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  src: string;
  alt: string;
  lazy?: boolean;
  responsive?: boolean;
  optimizationOptions?: ImageOptimizationOptions;
  fallbackSrc?: string;
  onLoad?: () => void;
  onError?: () => void;
}

export const OptimizedImage: React.FC<OptimizedImageProps> = ({
  src,
  alt,
  lazy = true,
  responsive = true,
  optimizationOptions = {},
  fallbackSrc,
  onLoad,
  onError,
  className = '',
  ...props
}) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [currentSrc, setCurrentSrc] = useState<string>('');
  const imgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;

    if (lazy) {
      // Set up lazy loading
      img.classList.add('lazy');
      if (responsive) {
        const { srcSet, sizes } = generateResponsiveImageUrls(src, optimizationOptions);
        img.dataset.srcset = srcSet;
        img.dataset.sizes = sizes;
      } else {
        img.dataset.src = generateOptimizedImageUrl(src, 800, optimizationOptions);
      }
      globalLazyLoader.observe(img);
    } else {
      // Load immediately
      if (responsive) {
        const { srcSet, sizes } = generateResponsiveImageUrls(src, optimizationOptions);
        img.srcset = srcSet;
        img.sizes = sizes;
      } else {
        img.src = generateOptimizedImageUrl(src, 800, optimizationOptions);
      }
    }

    return () => {
      if (lazy && img) {
        globalLazyLoader.unobserve(img);
      }
    };
  }, [src, lazy, responsive, optimizationOptions]);

  const handleLoad = () => {
    setIsLoaded(true);
    setHasError(false);
    onLoad?.();
  };

  const handleError = () => {
    setHasError(true);
    if (fallbackSrc && currentSrc !== fallbackSrc) {
      setCurrentSrc(fallbackSrc);
      if (imgRef.current) {
        imgRef.current.src = fallbackSrc;
      }
    }
    onError?.();
  };

  const imageClasses = [
    className,
    lazy ? 'lazy' : '',
    isLoaded ? 'loaded' : '',
    hasError ? 'error' : '',
    'transition-opacity duration-300',
    !isLoaded && lazy ? 'opacity-0' : 'opacity-100',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <img
      ref={imgRef}
      alt={alt}
      className={imageClasses}
      onLoad={handleLoad}
      onError={handleError}
      {...props}
    />
  );
};

// Placeholder component for loading states
export const ImagePlaceholder: React.FC<{
  width?: number;
  height?: number;
  className?: string;
}> = ({ width = 300, height = 200, className = '' }) => (
  <div
    data-testid="image-placeholder"
    className={`bg-gray-200 animate-pulse flex items-center justify-center ${className}`}
    style={{ width, height }}
  >
    <svg
      className="w-8 h-8 text-gray-400"
      fill="currentColor"
      viewBox="0 0 20 20"
      xmlns="http://www.w3.org/2000/svg"
    >
      <path
        fillRule="evenodd"
        d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z"
        clipRule="evenodd"
      />
    </svg>
  </div>
);

export default OptimizedImage;