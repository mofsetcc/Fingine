import { test, expect, Page } from '@playwright/test';

/**
 * User Acceptance Testing - Complete User Journeys
 * Tests critical user flows in production environment
 */

test.describe('User Acceptance Testing - Complete User Journeys', () => {
  let testUserEmail: string;
  let testUserPassword: string;

  test.beforeEach(async () => {
    // Generate unique test user for each test
    const timestamp = Date.now();
    testUserEmail = `uat_user_${timestamp}@test.kessan.app`;
    testUserPassword = 'TestUser123!';
  });

  test('Complete New User Onboarding Journey', async ({ page }) => {
    // Step 1: Navigate to homepage
    await page.goto('/');
    await expect(page).toHaveTitle(/Kessan/);
    
    // Verify homepage elements
    await expect(page.locator('[data-testid="market-indices"]')).toBeVisible();
    await expect(page.locator('[data-testid="hot-stocks-section"]')).toBeVisible();

    // Step 2: User Registration
    await page.click('[data-testid="register-button"]');
    await expect(page).toHaveURL(/.*\/register/);
    
    await page.fill('[data-testid="email-input"]', testUserEmail);
    await page.fill('[data-testid="password-input"]', testUserPassword);
    await page.fill('[data-testid="confirm-password-input"]', testUserPassword);
    await page.fill('[data-testid="display-name-input"]', 'UAT Test User');
    
    await page.click('[data-testid="register-submit"]');
    
    // Should redirect to email verification page
    await expect(page.locator('[data-testid="email-verification-message"]')).toBeVisible();

    // Step 3: Simulate email verification and login
    // In production, this would require actual email verification
    // For UAT, we'll navigate directly to login
    await page.goto('/login');
    
    await page.fill('[data-testid="login-email"]', testUserEmail);
    await page.fill('[data-testid="login-password"]', testUserPassword);
    await page.click('[data-testid="login-submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(/.*\/dashboard/);
    await expect(page.locator('[data-testid="user-profile-menu"]')).toBeVisible();

    // Step 4: Stock Search and Discovery
    await page.fill('[data-testid="stock-search-input"]', 'トヨタ');
    await page.waitForSelector('[data-testid="search-results"]');
    
    const searchResults = page.locator('[data-testid="search-result-item"]');
    await expect(searchResults.first()).toBeVisible();
    
    // Click on Toyota (7203)
    await searchResults.first().click();
    
    // Should navigate to stock analysis page
    await expect(page).toHaveURL(/.*\/stocks\/7203/);
    await expect(page.locator('[data-testid="stock-header"]')).toContainText('トヨタ');

    // Step 5: AI Analysis Generation
    await page.click('[data-testid="generate-analysis-button"]');
    
    // Wait for analysis to load
    await page.waitForSelector('[data-testid="ai-analysis-result"]', { timeout: 30000 });
    
    const analysisResult = page.locator('[data-testid="ai-analysis-result"]');
    await expect(analysisResult).toBeVisible();
    await expect(analysisResult.locator('[data-testid="analysis-rating"]')).toBeVisible();
    await expect(analysisResult.locator('[data-testid="confidence-score"]')).toBeVisible();

    // Step 6: Watchlist Management
    await page.click('[data-testid="add-to-watchlist-button"]');
    await expect(page.locator('[data-testid="watchlist-success-message"]')).toBeVisible();
    
    // Navigate to watchlist
    await page.click('[data-testid="watchlist-nav-link"]');
    await expect(page).toHaveURL(/.*\/watchlist/);
    
    const watchlistItems = page.locator('[data-testid="watchlist-item"]');
    await expect(watchlistItems).toHaveCount(1);
    await expect(watchlistItems.first()).toContainText('7203');

    // Step 7: Quota Usage Check
    await page.click('[data-testid="user-profile-menu"]');
    await page.click('[data-testid="profile-settings-link"]');
    
    await expect(page.locator('[data-testid="quota-usage-display"]')).toBeVisible();
    const quotaUsage = page.locator('[data-testid="ai-analysis-usage"]');
    await expect(quotaUsage).toContainText('1'); // Should show 1 analysis used
  });

  test('Subscription Upgrade Flow', async ({ page }) => {
    // Setup: Register and login user
    await registerAndLoginUser(page, testUserEmail, testUserPassword);

    // Step 1: Navigate to subscription page
    await page.click('[data-testid="user-profile-menu"]');
    await page.click('[data-testid="subscription-settings-link"]');
    
    await expect(page).toHaveURL(/.*\/subscription/);
    await expect(page.locator('[data-testid="current-plan"]')).toContainText('Free');

    // Step 2: View available plans
    const planCards = page.locator('[data-testid="plan-card"]');
    await expect(planCards).toHaveCount(3); // Free, Pro, Business
    
    const proPlan = page.locator('[data-testid="plan-card-pro"]');
    await expect(proPlan).toBeVisible();

    // Step 3: Initiate upgrade to Pro
    await proPlan.locator('[data-testid="upgrade-button"]').click();
    
    // Should open payment modal
    await expect(page.locator('[data-testid="payment-modal"]')).toBeVisible();

    // Step 4: Enter payment information (test card)
    await page.fill('[data-testid="card-number-input"]', '4242424242424242');
    await page.fill('[data-testid="card-expiry-input"]', '12/25');
    await page.fill('[data-testid="card-cvc-input"]', '123');
    await page.fill('[data-testid="cardholder-name-input"]', 'UAT Test User');

    await page.click('[data-testid="confirm-payment-button"]');

    // Step 5: Verify successful upgrade
    await page.waitForSelector('[data-testid="upgrade-success-message"]', { timeout: 10000 });
    await expect(page.locator('[data-testid="current-plan"]')).toContainText('Pro');

    // Step 6: Verify enhanced features
    await page.goto('/dashboard');
    
    // Should now have access to real-time data toggle
    await expect(page.locator('[data-testid="realtime-data-toggle"]')).toBeVisible();
    
    // Check increased quotas
    await page.click('[data-testid="user-profile-menu"]');
    await page.click('[data-testid="profile-settings-link"]');
    
    const dailyLimit = page.locator('[data-testid="daily-analysis-limit"]');
    await expect(dailyLimit).toContainText('100'); // Pro tier limit
  });

  test('Mobile Responsive User Journey', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    // Test mobile navigation and core features
    await page.goto('/');
    
    // Mobile menu should be visible
    await expect(page.locator('[data-testid="mobile-menu-button"]')).toBeVisible();
    
    // Test mobile search
    await page.click('[data-testid="mobile-search-button"]');
    await page.fill('[data-testid="mobile-search-input"]', 'ソニー');
    
    const mobileSearchResults = page.locator('[data-testid="mobile-search-results"]');
    await expect(mobileSearchResults).toBeVisible();
    
    // Test mobile stock analysis
    await mobileSearchResults.locator('[data-testid="search-result-item"]').first().click();
    
    // Mobile analysis view should be optimized
    await expect(page.locator('[data-testid="mobile-analysis-view"]')).toBeVisible();
    await expect(page.locator('[data-testid="mobile-chart-container"]')).toBeVisible();
  });

  test('Performance and Load Testing', async ({ page }) => {
    // Test page load performance
    const startTime = Date.now();
    await page.goto('/');
    const loadTime = Date.now() - startTime;
    
    // Homepage should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);

    // Test search performance
    const searchStartTime = Date.now();
    await page.fill('[data-testid="stock-search-input"]', 'トヨタ');
    await page.waitForSelector('[data-testid="search-results"]');
    const searchTime = Date.now() - searchStartTime;
    
    // Search should complete within 500ms
    expect(searchTime).toBeLessThan(500);

    // Test analysis generation performance
    await page.locator('[data-testid="search-result-item"]').first().click();
    
    const analysisStartTime = Date.now();
    await page.click('[data-testid="generate-analysis-button"]');
    await page.waitForSelector('[data-testid="ai-analysis-result"]', { timeout: 30000 });
    const analysisTime = Date.now() - analysisStartTime;
    
    // Analysis should complete within 15 seconds
    expect(analysisTime).toBeLessThan(15000);
  });

  test('Error Handling and Edge Cases', async ({ page }) => {
    await page.goto('/');

    // Test invalid stock ticker
    await page.goto('/stocks/INVALID');
    await expect(page.locator('[data-testid="stock-not-found-message"]')).toBeVisible();

    // Test network error handling
    await page.route('**/api/v1/market/indices', route => route.abort());
    await page.goto('/dashboard');
    
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();

    // Test form validation
    await page.goto('/register');
    await page.click('[data-testid="register-submit"]');
    
    await expect(page.locator('[data-testid="email-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="password-error"]')).toBeVisible();
  });

  test('Accessibility Compliance', async ({ page }) => {
    await page.goto('/');

    // Test keyboard navigation
    await page.keyboard.press('Tab');
    await expect(page.locator(':focus')).toBeVisible();

    // Test screen reader compatibility
    const searchInput = page.locator('[data-testid="stock-search-input"]');
    await expect(searchInput).toHaveAttribute('aria-label');

    // Test color contrast and visual elements
    const buttons = page.locator('button');
    for (let i = 0; i < await buttons.count(); i++) {
      const button = buttons.nth(i);
      await expect(button).toHaveCSS('cursor', 'pointer');
    }
  });
});

// Helper functions
async function registerAndLoginUser(page: Page, email: string, password: string) {
  // Register user
  await page.goto('/register');
  await page.fill('[data-testid="email-input"]', email);
  await page.fill('[data-testid="password-input"]', password);
  await page.fill('[data-testid="confirm-password-input"]', password);
  await page.fill('[data-testid="display-name-input"]', 'UAT Test User');
  await page.click('[data-testid="register-submit"]');

  // Login user
  await page.goto('/login');
  await page.fill('[data-testid="login-email"]', email);
  await page.fill('[data-testid="login-password"]', password);
  await page.click('[data-testid="login-submit"]');
  
  await expect(page).toHaveURL(/.*\/dashboard/);
}