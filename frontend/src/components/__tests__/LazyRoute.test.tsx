import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { LazyRoute } from '../LazyRoute';

// Mock LoadingSpinner component
jest.mock('../LoadingSpinner', () => {
  return {
    __esModule: true,
    default: function MockLoadingSpinner() {
      return <div data-testid="loading-spinner">Loading...</div>;
    },
  };
});

describe('LazyRoute', () => {
  it('should render children when loaded', () => {
    render(
      <LazyRoute>
        <div data-testid="child-component">Child Content</div>
      </LazyRoute>
    );

    expect(screen.getByTestId('child-component')).toBeInTheDocument();
  });

  it('should show default loading spinner as fallback', () => {
    const ThrowingComponent = () => {
      throw new Promise(() => {}); // Never resolves to keep in loading state
    };

    render(
      <LazyRoute>
        <ThrowingComponent />
      </LazyRoute>
    );

    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });

  it('should show custom fallback when provided', () => {
    const ThrowingComponent = () => {
      throw new Promise(() => {}); // Never resolves
    };

    const customFallback = <div data-testid="custom-fallback">Custom Loading...</div>;

    render(
      <LazyRoute fallback={customFallback}>
        <ThrowingComponent />
      </LazyRoute>
    );

    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.queryByTestId('loading-spinner')).not.toBeInTheDocument();
  });

  it('should handle Suspense correctly', () => {
    const SuspendingComponent = () => {
      throw new Promise(resolve => setTimeout(resolve, 100));
    };

    render(
      <LazyRoute>
        <SuspendingComponent />
      </LazyRoute>
    );

    // Should show loading spinner while suspended
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
  });
});