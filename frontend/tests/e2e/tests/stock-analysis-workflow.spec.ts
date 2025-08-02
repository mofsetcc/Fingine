/**
 * End-to-end tests for complete stock analysis workflow.
 */

import { expect, test } from '@playwright/test';

test.describe('Stock Analysis Workflow', () => {
  
  // Use authenticated state for all tests
  test.use({ storageState: 'tests/e2e/auth-state.json' });

  test('complete stock search and analysis flow', async ({ page }) => {
    // Navigate to dashboard
    await page.goto('/dashboard');
    
    // Verify dashboard loads
    await expect(page.locator('h1')).toContainText('Market Overview');
    await expect(page.locator('[data-testid="market-indices"]')).toBeVisible();
    
    // Use stock search
    const searchInput = page.locator('[data-testid="stock-search-input"]');
    await expect(searchInput).toBeVisible();
    
    // Search for Toyota
    await searchInput.fill('Toyota');
    
    // Wait for search results
    await expect(page.locator('[data-testid="search-results"]')).toBeVisible();
    await expect(page.locator('[data-testid="search-result-item"]').first()).toBeVisible();
    
    // Verify search results contain Toyota
    const firstResult = page.locator('[data-testid="search-result-item"]').first();
    await expect(firstResult).toContainText('7203');
    await expect(firstResult).toContainText('トヨタ自動車');
    
    // Click on Toyota result
    await firstResult.click();
    
    // Should navigate to stock analysis page
    await expect(page).toHaveURL('/stocks/7203');
    
    // Verify stock analysis page loads
    await expect(page.locator('h1')).toContainText('トヨタ自動車');
    await expect(page.locator('[data-testid="stock-ticker"]')).toContainText('7203');
    
    // Verify key sections are present
    await expect(page.locator('[data-testid="ai-analysis-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="price-chart-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="financial-data-section"]')).toBeVisible();
    await expect(page.locator('[data-testid="news-section"]')).toBeVisible();
  });

  test('AI analysis generation flow', async ({ page }) => {
    // Navigate to Toyota stock page
    await page.goto('/stocks/7203');
    
    // Wait for page to load
    await expect(page.locator('[data-testid="stock-ticker"]')).toContainText('7203');
    
    // Check if AI analysis is already available
    const analysisSection = page.locator('[data-testid="ai-analysis-section"]');
    await expect(analysisSection).toBeVisible();
    
    // If no analysis exists, generate new one
    const generateButton = page.locator('[data-testid="generate-analysis-button"]');
    if (await generateButton.isVisible()) {
      // Click generate analysis
      await generateButton.click();
      
      // Should show loading state
      await expect(page.locator('[data-testid="analysis-loading"]')).toBeVisible();
      
      // Wait for analysis to complete (with timeout)
      await expect(page.locator('[data-testid="analysis-result"]')).toBeVisible({ timeout: 30000 });
    }
    
    // Verify analysis components
    await expect(page.locator('[data-testid="analysis-rating"]')).toBeVisible();
    await expect(page.locator('[data-testid="analysis-confidence"]')).toBeVisible();
    await expect(page.locator('[data-testid="key-factors"]')).toBeVisible();
    await expect(page.locator('[data-testid="price-target"]')).toBeVisible();
    await expect(page.locator('[data-testid="risk-factors"]')).toBeVisible();
    
    // Verify analysis content
    const rating = page.locator('[data-testid="analysis-rating"]');
    await expect(rating).toContainText(/Bullish|Bearish|Neutral/);
    
    const confidence = page.locator('[data-testid="analysis-confidence"]');
    await expect(confidence).toContainText('%');
  });

  test('stock price chart interaction', async ({ page }) => {
    // Navigate to Toyota stock page
    await page.goto('/stocks/7203');
    
    // Wait for chart to load
    const chartContainer = page.locator('[data-testid="price-chart"]');
    await expect(chartContainer).toBeVisible();
    
    // Test chart time period selection
    const timeButtons = page.locator('[data-testid="chart-time-period"] button');
    await expect(timeButtons).toHaveCount(5); // 1D, 1W, 1M, 3M, 1Y
    
    // Click on 1M button
    await page.click('[data-testid="chart-1M"]');
    
    // Chart should update (wait for loading to complete)
    await page.waitForTimeout(2000);
    
    // Verify chart data is displayed
    await expect(page.locator('[data-testid="chart-data"]')).toBeVisible();
    
    // Test chart type toggle (candlestick vs line)
    const chartTypeToggle = page.locator('[data-testid="chart-type-toggle"]');
    if (await chartTypeToggle.isVisible()) {
      await chartTypeToggle.click();
      await page.waitForTimeout(1000);
    }
  });

  test('financial data display', async ({ page }) => {
    // Navigate to Toyota stock page
    await page.goto('/stocks/7203');
    
    // Verify financial data section
    const financialSection = page.locator('[data-testid="financial-data-section"]');
    await expect(financialSection).toBeVisible();
    
    // Check key financial metrics
    await expect(page.locator('[data-testid="revenue"]')).toBeVisible();
    await expect(page.locator('[data-testid="operating-income"]')).toBeVisible();
    await expect(page.locator('[data-testid="net-income"]')).toBeVisible();
    await expect(page.locator('[data-testid="total-assets"]')).toBeVisible();
    
    // Test financial data tabs (quarterly vs annual)
    const quarterlyTab = page.locator('[data-testid="quarterly-tab"]');
    const annualTab = page.locator('[data-testid="annual-tab"]');
    
    if (await quarterlyTab.isVisible()) {
      await quarterlyTab.click();
      await expect(page.locator('[data-testid="quarterly-data"]')).toBeVisible();
    }
    
    if (await annualTab.isVisible()) {
      await annualTab.click();
      await expect(page.locator('[data-testid="annual-data"]')).toBeVisible();
    }
  });

  test('news and sentiment analysis', async ({ page }) => {
    // Navigate to Toyota stock page
    await page.goto('/stocks/7203');
    
    // Verify news section
    const newsSection = page.locator('[data-testid="news-section"]');
    await expect(newsSection).toBeVisible();
    
    // Check for news articles
    const newsArticles = page.locator('[data-testid="news-article"]');
    await expect(newsArticles.first()).toBeVisible();
    
    // Verify sentiment indicators
    const sentimentIndicators = page.locator('[data-testid="sentiment-indicator"]');
    if (await sentimentIndicators.first().isVisible()) {
      await expect(sentimentIndicators.first()).toContainText(/Positive|Negative|Neutral/);
    }
    
    // Test news article interaction
    const firstArticle = newsArticles.first();
    await expect(firstArticle.locator('[data-testid="article-title"]')).toBeVisible();
    await expect(firstArticle.locator('[data-testid="article-source"]')).toBeVisible();
    await expect(firstArticle.locator('[data-testid="article-date"]')).toBeVisible();
    
    // Click on news article (should open in new tab or modal)
    await firstArticle.click();
  });

  test('watchlist management from stock page', async ({ page }) => {
    // Navigate to Toyota stock page
    await page.goto('/stocks/7203');
    
    // Find add to watchlist button
    const addToWatchlistButton = page.locator('[data-testid="add-to-watchlist"]');
    
    // If stock is not in watchlist, add it
    if (await addToWatchlistButton.isVisible()) {
      await addToWatchlistButton.click();
      
      // Should show success message
      await expect(page.locator('[data-testid="watchlist-success"]')).toBeVisible();
      
      // Button should change to "Remove from Watchlist"
      await expect(page.locator('[data-testid="remove-from-watchlist"]')).toBeVisible();
    }
    
    // Navigate to watchlist page to verify
    await page.goto('/watchlist');
    
    // Should see Toyota in watchlist
    await expect(page.locator('[data-testid="watchlist-item-7203"]')).toBeVisible();
    
    // Go back to stock page
    await page.goto('/stocks/7203');
    
    // Remove from watchlist
    const removeButton = page.locator('[data-testid="remove-from-watchlist"]');
    if (await removeButton.isVisible()) {
      await removeButton.click();
      
      // Should show removal confirmation
      await expect(page.locator('[data-testid="watchlist-removed"]')).toBeVisible();
    }
  });

  test('stock comparison feature', async ({ page }) => {
    // Navigate to Toyota stock page
    await page.goto('/stocks/7203');
    
    // Look for compare button
    const compareButton = page.locator('[data-testid="compare-stocks"]');
    
    if (await compareButton.isVisible()) {
      await compareButton.click();
      
      // Should open comparison modal or navigate to comparison page
      await expect(page.locator('[data-testid="stock-comparison"]')).toBeVisible();
      
      // Add Sony for comparison
      const addStockInput = page.locator('[data-testid="add-comparison-stock"]');
      await addStockInput.fill('Sony');
      
      // Select Sony from dropdown
      await page.click('[data-testid="comparison-suggestion-6758"]');
      
      // Should show comparison data
      await expect(page.locator('[data-testid="comparison-table"]')).toBeVisible();
      await expect(page.locator('[data-testid="comparison-chart"]')).toBeVisible();
    }
  });

  test('mobile responsiveness on stock page', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    
    // Navigate to Toyota stock page
    await page.goto('/stocks/7203');
    
    // Verify mobile layout
    await expect(page.locator('[data-testid="mobile-stock-header"]')).toBeVisible();
    
    // Check that sections are stacked vertically
    const sections = page.locator('[data-testid*="section"]');
    const sectionCount = await sections.count();
    expect(sectionCount).toBeGreaterThan(0);
    
    // Test mobile navigation
    const mobileMenu = page.locator('[data-testid="mobile-menu-button"]');
    if (await mobileMenu.isVisible()) {
      await mobileMenu.click();
      await expect(page.locator('[data-testid="mobile-menu"]')).toBeVisible();
    }
    
    // Test chart responsiveness
    const chart = page.locator('[data-testid="price-chart"]');
    await expect(chart).toBeVisible();
    
    // Chart should fit mobile screen
    const chartBox = await chart.boundingBox();
    expect(chartBox?.width).toBeLessThanOrEqual(375);
  });

  test('error handling for invalid stock ticker', async ({ page }) => {
    // Navigate to invalid stock page
    await page.goto('/stocks/INVALID');
    
    // Should show error page or message
    await expect(page.locator('[data-testid="stock-not-found"]')).toBeVisible();
    await expect(page.locator('[data-testid="stock-not-found"]')).toContainText('not found');
    
    // Should provide navigation back to search
    const backToSearchButton = page.locator('[data-testid="back-to-search"]');
    await expect(backToSearchButton).toBeVisible();
    
    await backToSearchButton.click();
    
    // Should navigate back to dashboard or search
    await expect(page).toHaveURL('/dashboard');
  });

  test('performance monitoring', async ({ page }) => {
    // Navigate to Toyota stock page
    await page.goto('/stocks/7203');
    
    // Measure page load performance
    const performanceEntries = await page.evaluate(() => {
      return JSON.stringify(performance.getEntriesByType('navigation'));
    });
    
    const navigation = JSON.parse(performanceEntries)[0];
    
    // Page should load within reasonable time
    expect(navigation.loadEventEnd - navigation.loadEventStart).toBeLessThan(5000);
    
    // Check for performance metrics
    const performanceMetrics = await page.evaluate(() => {
      return {
        domContentLoaded: performance.timing.domContentLoadedEventEnd - performance.timing.navigationStart,
        loadComplete: performance.timing.loadEventEnd - performance.timing.navigationStart,
        firstPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-paint')?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByType('paint').find(entry => entry.name === 'first-contentful-paint')?.startTime || 0
      };
    });
    
    // Performance thresholds
    expect(performanceMetrics.domContentLoaded).toBeLessThan(3000);
    expect(performanceMetrics.loadComplete).toBeLessThan(5000);
    expect(performanceMetrics.firstPaint).toBeLessThan(2000);
    expect(performanceMetrics.firstContentfulPaint).toBeLessThan(2500);
  });
});