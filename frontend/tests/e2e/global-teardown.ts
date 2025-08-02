/**
 * Global teardown for Playwright tests.
 * Cleans up test data and resources.
 */

import { chromium, FullConfig } from '@playwright/test';
import fs from 'fs';

async function globalTeardown(config: FullConfig) {
  console.log('🧹 Starting global teardown for E2E tests...');

  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Clean up test data
    await cleanupTestData(page);

    // Remove authentication state file
    if (fs.existsSync('tests/e2e/auth-state.json')) {
      fs.unlinkSync('tests/e2e/auth-state.json');
      console.log('✅ Authentication state file removed');
    }

  } catch (error) {
    console.error('❌ Global teardown failed:', error);
    // Don't throw error in teardown to avoid masking test failures
  } finally {
    await browser.close();
  }

  console.log('✅ Global teardown completed');
}

async function cleanupTestData(page: any) {
  console.log('🗑️ Cleaning up test data...');
  
  try {
    // Call backend API to clean up test data
    const response = await page.request.post('http://localhost:8000/api/v1/test/cleanup', {
      data: {
        cleanup_users: ['e2e-test@example.com'],
        cleanup_test_stocks: true,
        cleanup_test_plans: true
      }
    });

    if (response.ok()) {
      console.log('✅ Test data cleanup completed');
    } else {
      console.warn('⚠️ Test data cleanup failed, some data may remain');
    }
  } catch (error) {
    console.warn('⚠️ Test data cleanup error:', error);
  }
}

export default globalTeardown;