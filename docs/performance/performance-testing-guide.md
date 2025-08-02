# Performance Testing Guide

## Overview

This guide covers the performance testing setup for the Japanese Stock Analysis Platform, including Lighthouse CI integration and fallback performance tests.

## Performance Testing Tools

### 1. Lighthouse CI

Lighthouse CI is our primary performance testing tool that runs automated audits on our frontend application.

#### Configuration

The Lighthouse CI configuration is located in `frontend/.lighthouserc.js`:

```javascript
module.exports = {
  ci: {
    collect: {
      staticDistDir: './dist',
      numberOfRuns: 1,
      settings: {
        chromeFlags: '--no-sandbox --disable-dev-shm-usage --headless'
      }
    },
    assert: {
      assertions: {
        'categories:performance': ['warn', { minScore: 0.6 }],
        'categories:accessibility': ['warn', { minScore: 0.8 }],
        // ... more assertions
      }
    }
  }
};
```

#### Performance Budgets

We maintain the following performance budgets:

- **Performance Score**: ≥ 60% (warning threshold)
- **Accessibility Score**: ≥ 80% (warning threshold)
- **First Contentful Paint**: ≤ 4000ms
- **Largest Contentful Paint**: ≤ 5000ms
- **Cumulative Layout Shift**: ≤ 0.2
- **Total Blocking Time**: ≤ 1000ms

### 2. Fallback Performance Tests

When Lighthouse CI fails, we run a custom performance test script that checks:

- Build output validation
- Bundle size analysis
- Performance budget compliance

#### Running Performance Tests Locally

```bash
# Build the frontend
cd frontend
npm run build

# Run Lighthouse CI
npx lhci autorun

# Or run fallback performance test
npm run test:performance
```

## CI/CD Integration

### GitHub Actions Workflow

The performance tests are integrated into our CI/CD pipeline:

```yaml
performance-tests:
  name: Performance Tests
  runs-on: ubuntu-latest
  needs: [frontend-tests]
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  
  steps:
    - name: Build frontend for production
      run: npm run build
      
    - name: Run Lighthouse CI with static files
      run: |
        if lhci collect --staticDistDir=./dist --numberOfRuns=1; then
          lhci assert --config=.lighthouserc.js
        else
          npm run test:performance
        fi
```

### Performance Test Results

Performance test results are:

1. **Uploaded as artifacts** for manual review
2. **Commented on pull requests** (when applicable)
3. **Stored in temporary public storage** via Lighthouse CI

## Troubleshooting

### Common Issues

#### 1. "Unable to automatically determine staticDistDir"

**Solution**: Ensure the build directory exists and contains the built files:

```bash
npm run build
ls -la dist/  # Should show index.html and assets/
```

#### 2. Chrome/Chromium Issues in CI

**Solution**: The configuration includes appropriate Chrome flags for CI environments:

```javascript
chromeFlags: [
  '--no-sandbox',
  '--disable-dev-shm-usage',
  '--headless',
  '--disable-gpu'
]
```

#### 3. Performance Budget Failures

**Solution**: 
- Review the specific metrics that failed
- Optimize bundle sizes, images, or code splitting
- Consider adjusting budgets if they're too strict for the CI environment

### Debugging Performance Issues

1. **Check build output**:
   ```bash
   npm run build
   npm run test:performance
   ```

2. **Run Lighthouse locally**:
   ```bash
   npm run build
   npm run preview &
   npx lighthouse http://localhost:4173 --view
   ```

3. **Analyze bundle sizes**:
   ```bash
   npm run build
   npx vite-bundle-analyzer dist/
   ```

## Performance Optimization Tips

### 1. Bundle Size Optimization

- Use code splitting with React.lazy()
- Implement tree shaking
- Optimize dependencies
- Use dynamic imports for large libraries

### 2. Image Optimization

- Use WebP format when possible
- Implement lazy loading
- Optimize image sizes for different screen densities
- Use responsive images

### 3. Code Optimization

- Minimize JavaScript execution time
- Reduce unused CSS
- Optimize critical rendering path
- Use service workers for caching

### 4. Network Optimization

- Enable compression (gzip/brotli)
- Use CDN for static assets
- Implement proper caching headers
- Minimize HTTP requests

## Monitoring and Alerts

### Performance Monitoring

We monitor the following metrics in production:

- Core Web Vitals (LCP, FID, CLS)
- Time to First Byte (TTFB)
- First Contentful Paint (FCP)
- Bundle sizes and load times

### Setting Up Alerts

Configure alerts for:

- Performance score drops below 70%
- Bundle size increases by more than 20%
- Core Web Vitals exceed thresholds
- Build failures in performance tests

## Best Practices

1. **Run performance tests on every main branch push**
2. **Review performance impact of new features**
3. **Set realistic performance budgets**
4. **Monitor performance trends over time**
5. **Optimize for mobile devices**
6. **Test with slow network conditions**

## Resources

- [Lighthouse CI Documentation](https://github.com/GoogleChrome/lighthouse-ci)
- [Web Vitals](https://web.dev/vitals/)
- [Performance Budgets](https://web.dev/performance-budgets-101/)
- [Vite Performance Guide](https://vitejs.dev/guide/performance.html)