/**
 * End-to-end tests for user registration and authentication flow.
 */

import { expect, test } from '@playwright/test';

test.describe('User Registration and Authentication Flow', () => {
  
  test('complete user registration flow', async ({ page }) => {
    // Navigate to registration page
    await page.goto('/register');
    
    // Verify registration form is visible
    await expect(page.locator('h1')).toContainText('Create Account');
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('input[name="displayName"]')).toBeVisible();
    
    // Fill registration form
    const testEmail = `test-${Date.now()}@example.com`;
    await page.fill('input[name="email"]', testEmail);
    await page.fill('input[name="password"]', 'SecurePassword123!');
    await page.fill('input[name="displayName"]', 'Test User');
    
    // Submit registration
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard after successful registration
    await expect(page).toHaveURL('/dashboard');
    
    // Verify user is logged in
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-display-name"]')).toContainText('Test User');
    
    // Verify welcome message or onboarding
    await expect(page.locator('[data-testid="welcome-message"]')).toBeVisible();
  });

  test('user login flow', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Verify login form
    await expect(page.locator('h1')).toContainText('Sign In');
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    
    // Fill login form with test user credentials
    await page.fill('input[name="email"]', 'e2e-test@example.com');
    await page.fill('input[name="password"]', 'TestPassword123!');
    
    // Submit login
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    
    // Verify user is logged in
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('OAuth login flow (Google)', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Click Google OAuth button
    await page.click('[data-testid="google-oauth-button"]');
    
    // Note: In real E2E tests, you would need to handle OAuth flow
    // This might involve mocking OAuth responses or using test OAuth providers
    // For now, we'll verify the button exists and is clickable
    
    // Verify OAuth button is present
    await expect(page.locator('[data-testid="google-oauth-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="line-oauth-button"]')).toBeVisible();
  });

  test('password reset flow', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Click forgot password link
    await page.click('[data-testid="forgot-password-link"]');
    
    // Should navigate to password reset page
    await expect(page).toHaveURL('/forgot-password');
    
    // Fill email for password reset
    await page.fill('input[name="email"]', 'e2e-test@example.com');
    
    // Submit password reset request
    await page.click('button[type="submit"]');
    
    // Should show success message
    await expect(page.locator('[data-testid="reset-success-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="reset-success-message"]')).toContainText('reset link has been sent');
  });

  test('user profile management', async ({ page, context }) => {
    // Use authenticated state
    await context.addInitScript(() => {
      localStorage.setItem('auth_token', process.env.E2E_AUTH_TOKEN || '');
    });
    
    // Navigate to profile page
    await page.goto('/profile');
    
    // Verify profile form
    await expect(page.locator('h1')).toContainText('Profile Settings');
    await expect(page.locator('input[name="displayName"]')).toBeVisible();
    await expect(page.locator('select[name="timezone"]')).toBeVisible();
    
    // Update profile information
    await page.fill('input[name="displayName"]', 'Updated E2E User');
    await page.selectOption('select[name="timezone"]', 'America/New_York');
    
    // Update notification preferences
    await page.check('input[name="emailNotifications"]');
    await page.uncheck('input[name="pushNotifications"]');
    
    // Save changes
    await page.click('button[data-testid="save-profile"]');
    
    // Should show success message
    await expect(page.locator('[data-testid="profile-success-message"]')).toBeVisible();
    
    // Verify changes are saved
    await page.reload();
    await expect(page.locator('input[name="displayName"]')).toHaveValue('Updated E2E User');
    await expect(page.locator('select[name="timezone"]')).toHaveValue('America/New_York');
  });

  test('user logout flow', async ({ page, context }) => {
    // Use authenticated state
    await context.addInitScript(() => {
      localStorage.setItem('auth_token', process.env.E2E_AUTH_TOKEN || '');
    });
    
    // Navigate to dashboard
    await page.goto('/dashboard');
    
    // Verify user is logged in
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
    
    // Click user menu
    await page.click('[data-testid="user-menu"]');
    
    // Click logout
    await page.click('[data-testid="logout-button"]');
    
    // Should redirect to login page
    await expect(page).toHaveURL('/login');
    
    // Verify user is logged out
    await expect(page.locator('[data-testid="user-menu"]')).not.toBeVisible();
    
    // Try to access protected page
    await page.goto('/dashboard');
    
    // Should redirect back to login
    await expect(page).toHaveURL('/login');
  });

  test('form validation errors', async ({ page }) => {
    // Navigate to registration page
    await page.goto('/register');
    
    // Try to submit empty form
    await page.click('button[type="submit"]');
    
    // Should show validation errors
    await expect(page.locator('[data-testid="email-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="password-error"]')).toBeVisible();
    
    // Fill invalid email
    await page.fill('input[name="email"]', 'invalid-email');
    await page.click('button[type="submit"]');
    
    // Should show email format error
    await expect(page.locator('[data-testid="email-error"]')).toContainText('valid email');
    
    // Fill weak password
    await page.fill('input[name="email"]', 'valid@example.com');
    await page.fill('input[name="password"]', '123');
    await page.click('button[type="submit"]');
    
    // Should show password strength error
    await expect(page.locator('[data-testid="password-error"]')).toContainText('password must');
  });

  test('duplicate email registration', async ({ page }) => {
    // Navigate to registration page
    await page.goto('/register');
    
    // Try to register with existing email
    await page.fill('input[name="email"]', 'e2e-test@example.com'); // Already exists
    await page.fill('input[name="password"]', 'SecurePassword123!');
    await page.fill('input[name="displayName"]', 'Duplicate User');
    
    // Submit registration
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('[data-testid="registration-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="registration-error"]')).toContainText('already exists');
  });

  test('invalid login credentials', async ({ page }) => {
    // Navigate to login page
    await page.goto('/login');
    
    // Try to login with invalid credentials
    await page.fill('input[name="email"]', 'nonexistent@example.com');
    await page.fill('input[name="password"]', 'WrongPassword123!');
    
    // Submit login
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('[data-testid="login-error"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid credentials');
    
    // Should remain on login page
    await expect(page).toHaveURL('/login');
  });
});