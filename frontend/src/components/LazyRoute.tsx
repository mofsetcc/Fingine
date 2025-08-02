import React, { Suspense } from 'react';
import LoadingSpinner from './LoadingSpinner';

interface LazyRouteProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

/**
 * Wrapper component for lazy-loaded routes with loading fallback
 */
export const LazyRoute: React.FC<LazyRouteProps> = ({ 
  children, 
  fallback = <LoadingSpinner /> 
}) => {
  return (
    <Suspense fallback={fallback}>
      {children}
    </Suspense>
  );
};

/**
 * Higher-order component for creating lazy-loaded components
 */
export function withLazyLoading<T extends Record<string, any>>(
  importFn: () => Promise<{ default: React.ComponentType<T> }>,
  fallback?: React.ReactNode
) {
  const LazyComponent = React.lazy(importFn);
  
  return (props: T) => (
    <LazyRoute fallback={fallback}>
      <LazyComponent {...props} />
    </LazyRoute>
  );
}

export default LazyRoute;