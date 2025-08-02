/**
 * Global setup for Playwright tests.
 * Sets up test database and authentication state.
 */

import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global setup for E2E tests...');

  // Start browser for setup
  const browser = await chromium.launch();
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    // Wait for backend to be ready
    console.log('⏳ Waiting for backend to be ready...');
    await page.goto('http://localhost:8000/health');
    await page.waitForResponse(response => 
      response.url().includes('/health') && response.status() === 200
    );
    console.log('✅ Backend is ready');

    // Wait for frontend to be ready
    console.log('⏳ Waiting for frontend to be ready...');
    await page.goto('http://localhost:3000');
    await page.waitForLoadState('networkidle');
    console.log('✅ Frontend is ready');

    // Set up test data
    await setupTestData(page);

    // Create authenticated user state
    await setupAuthenticatedUser(page);

  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }

  console.log('✅ Global setup completed');
}

async function setupTestData(page: any) {
  console.log('📊 Setting up test data...');
  
  // Call backend API to set up test data
  const response = await page.request.post('http://localhost:8000/api/v1/test/setup', {
    data: {
      stocks: [
        {
          ticker: '7203',
          company_name_jp: 'トヨタ自動車株式会社',
          company_name_en: 'Toyota Motor Corporation',
          sector_jp: '輸送用機器',
          industry_jp: '自動車'
        },
        {
          ticker: '6758',
          company_name_jp: 'ソニーグループ株式会社',
          company_name_en: 'Sony Group Corporation',
          sector_jp: '電気機器',
          industry_jp: 'エレクトロニクス'
        }
      ],
      plans: [
        {
          plan_name: 'free',
          price_monthly: 0,
          api_quota_daily: 10,
          ai_analysis_quota_daily: 0
        },
        {
          plan_name: 'pro',
          price_monthly: 2980,
          api_quota_daily: 100,
          ai_analysis_quota_daily: 20
        }
      ]
    }
  });

  if (!response.ok()) {
    console.warn('⚠️ Test data setup failed, continuing with existing data');
  } else {
    console.log('✅ Test data setup completed');
  }
}

async function setupAuthenticatedUser(page: any) {
  console.log('👤 Setting up authenticated user state...');
  
  // Register a test user
  const testUser = {
    email: 'e2e-test@example.com',
    password: 'TestPassword123!',
    display_name: 'E2E Test User'
  };

  try {
    // Try to register the user (might already exist)
    await page.request.post('http://localhost:8000/api/v1/auth/register', {
      data: testUser
    });
  } catch (error) {
    // User might already exist, that's okay
    console.log('ℹ️ Test user might already exist, continuing...');
  }

  // Login and save authentication state
  const loginResponse = await page.request.post('http://localhost:8000/api/v1/auth/login', {
    data: {
      email: testUser.email,
      password: testUser.password
    }
  });

  if (loginResponse.ok()) {
    const loginData = await loginResponse.json();
    
    // Save authentication state to file
    await page.context().storageState({ path: 'tests/e2e/auth-state.json' });
    
    // Also save token for API calls
    process.env.E2E_AUTH_TOKEN = loginData.access_token;
    
    console.log('✅ Authenticated user state saved');
  } else {
    console.error('❌ Failed to authenticate test user');
    throw new Error('Authentication setup failed');
  }
}

export default globalSetup;