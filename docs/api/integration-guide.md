# Project Kessan API Integration Guide

This guide provides comprehensive examples and best practices for integrating with the Project Kessan API.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Stock Data Integration](#stock-data-integration)
4. [AI Analysis Integration](#ai-analysis-integration)
5. [Watchlist Management](#watchlist-management)
6. [Subscription Management](#subscription-management)
7. [Error Handling](#error-handling)
8. [Rate Limiting](#rate-limiting)
9. [SDKs and Libraries](#sdks-and-libraries)

## Quick Start

### Base URL
```
Production: https://api.kessan.ai/api/v1
Staging: https://staging-api.kessan.ai/api/v1
Development: http://localhost:8000/api/v1
```

### Basic Request Example

```bash
curl -X GET "https://api.kessan.ai/api/v1/stocks/search?query=toyota" \
  -H "Accept: application/json"
```

## Authentication

### 1. User Registration

```javascript
// JavaScript/Node.js Example
const registerUser = async (email, password, displayName) => {
  const response = await fetch('https://api.kessan.ai/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email,
      password: password,
      display_name: displayName
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }
  
  return await response.json();
};

// Usage
try {
  const result = await registerUser('user@example.com', 'securePassword123', 'John Doe');
  console.log('Registration successful:', result.message);
} catch (error) {
  console.error('Registration failed:', error.message);
}
```

```python
# Python Example
import requests
import json

def register_user(email, password, display_name=None):
    url = "https://api.kessan.ai/api/v1/auth/register"
    payload = {
        "email": email,
        "password": password
    }
    if display_name:
        payload["display_name"] = display_name
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 201:
        return response.json()
    else:
        raise Exception(f"Registration failed: {response.json().get('detail', 'Unknown error')}")

# Usage
try:
    result = register_user("user@example.com", "securePassword123", "John Doe")
    print(f"Registration successful: {result['message']}")
except Exception as e:
    print(f"Registration failed: {e}")
```

### 2. User Login

```javascript
// JavaScript/Node.js Example
const loginUser = async (email, password, rememberMe = false) => {
  const response = await fetch('https://api.kessan.ai/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email,
      password: password,
      remember_me: rememberMe
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }
  
  const data = await response.json();
  
  // Store tokens securely
  localStorage.setItem('access_token', data.data.access_token);
  localStorage.setItem('refresh_token', data.data.refresh_token);
  
  return data;
};
```

```python
# Python Example
import requests

class KessanAPIClient:
    def __init__(self, base_url="https://api.kessan.ai/api/v1"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
    
    def login(self, email, password, remember_me=False):
        url = f"{self.base_url}/auth/login"
        payload = {
            "email": email,
            "password": password,
            "remember_me": remember_me
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            self.access_token = data['data']['access_token']
            self.refresh_token = data['data']['refresh_token']
            return data
        else:
            raise Exception(f"Login failed: {response.json().get('detail', 'Unknown error')}")
    
    def get_headers(self):
        if not self.access_token:
            raise Exception("Not authenticated. Please login first.")
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

# Usage
client = KessanAPIClient()
try:
    result = client.login("user@example.com", "securePassword123")
    print("Login successful")
except Exception as e:
    print(f"Login failed: {e}")
```

### 3. OAuth Authentication

```javascript
// Google OAuth Example
const googleOAuthLogin = async (googleAccessToken) => {
  const response = await fetch('https://api.kessan.ai/api/v1/auth/oauth/google', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      access_token: googleAccessToken
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'OAuth login failed');
  }
  
  const data = await response.json();
  
  // Store tokens
  localStorage.setItem('access_token', data.data.access_token);
  localStorage.setItem('refresh_token', data.data.refresh_token);
  
  return data;
};
```

### 4. Token Refresh

```javascript
// Automatic token refresh
const refreshToken = async () => {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }
  
  const response = await fetch('https://api.kessan.ai/api/v1/auth/refresh', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${refreshToken}`,
      'Content-Type': 'application/json',
    }
  });
  
  if (!response.ok) {
    // Refresh token expired, redirect to login
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    throw new Error('Session expired. Please login again.');
  }
  
  const data = await response.json();
  localStorage.setItem('access_token', data.data.access_token);
  
  return data.data.access_token;
};

// Wrapper function with automatic retry
const apiRequest = async (url, options = {}) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers
    }
  });
  
  if (response.status === 401) {
    // Try to refresh token
    try {
      const newToken = await refreshToken();
      // Retry original request with new token
      return await fetch(url, {
        ...options,
        headers: {
          'Authorization': `Bearer ${newToken}`,
          'Content-Type': 'application/json',
          ...options.headers
        }
      });
    } catch (error) {
      // Redirect to login
      window.location.href = '/login';
      throw error;
    }
  }
  
  return response;
};
```

## Stock Data Integration

### 1. Stock Search

```javascript
// Search for stocks
const searchStocks = async (query, limit = 20) => {
  const url = new URL('https://api.kessan.ai/api/v1/stocks/search');
  url.searchParams.append('query', query);
  url.searchParams.append('limit', limit.toString());
  
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error('Search failed');
  }
  
  return await response.json();
};

// Usage
const searchResults = await searchStocks('toyota');
console.log(`Found ${searchResults.total_results} results`);
searchResults.results.forEach(stock => {
  console.log(`${stock.ticker}: ${stock.company_name_jp} (${stock.relevance_score})`);
});
```

```python
# Python Example
def search_stocks(client, query, limit=20, include_inactive=False):
    url = f"{client.base_url}/stocks/search"
    params = {
        "query": query,
        "limit": limit,
        "include_inactive": include_inactive
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Search failed: {response.json().get('detail', 'Unknown error')}")

# Usage
results = search_stocks(client, "toyota")
print(f"Found {results['total_results']} results")
for stock in results['results']:
    print(f"{stock['ticker']}: {stock['company_name_jp']} ({stock['relevance_score']})")
```

### 2. Get Stock Details

```javascript
// Get detailed stock information
const getStockDetail = async (ticker) => {
  const response = await fetch(`https://api.kessan.ai/api/v1/stocks/${ticker}`);
  
  if (!response.ok) {
    if (response.status === 404) {
      throw new Error(`Stock ${ticker} not found`);
    }
    throw new Error('Failed to get stock details');
  }
  
  return await response.json();
};

// Usage
try {
  const toyotaStock = await getStockDetail('7203');
  console.log(`${toyotaStock.company_name_jp}: ¥${toyotaStock.current_price}`);
  console.log(`Change: ${toyotaStock.price_change_percent}%`);
  console.log(`P/E Ratio: ${toyotaStock.pe_ratio}`);
} catch (error) {
  console.error('Error:', error.message);
}
```

### 3. Get Price History

```javascript
// Get historical price data
const getPriceHistory = async (ticker, period = '1y', interval = '1d') => {
  const url = new URL(`https://api.kessan.ai/api/v1/stocks/${ticker}/price-history`);
  url.searchParams.append('period', period);
  url.searchParams.append('interval', interval);
  
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error('Failed to get price history');
  }
  
  return await response.json();
};

// Usage for charting
const priceData = await getPriceHistory('7203', '6m', '1d');
const chartData = priceData.data.map(point => ({
  date: new Date(point.date),
  open: point.open,
  high: point.high,
  low: point.low,
  close: point.close,
  volume: point.volume
}));

// Use with Chart.js, D3.js, or other charting libraries
```

### 4. Get Market Indices

```javascript
// Get market indices (Nikkei 225, TOPIX)
const getMarketIndices = async () => {
  const response = await fetch('https://api.kessan.ai/api/v1/stocks/market/indices');
  
  if (!response.ok) {
    throw new Error('Failed to get market indices');
  }
  
  return await response.json();
};

// Usage
const indices = await getMarketIndices();
indices.forEach(index => {
  console.log(`${index.name}: ${index.value} (${index.change_percent}%)`);
});
```

### 5. Get Hot Stocks

```javascript
// Get hot stocks (gainers, losers, most traded)
const getHotStocks = async () => {
  const response = await fetch('https://api.kessan.ai/api/v1/stocks/market/hot-stocks');
  
  if (!response.ok) {
    throw new Error('Failed to get hot stocks');
  }
  
  return await response.json();
};

// Usage
const hotStocks = await getHotStocks();

console.log('Top Gainers:');
hotStocks.gainers.slice(0, 5).forEach(stock => {
  console.log(`${stock.ticker}: ${stock.company_name_jp} (+${stock.price_change_percent}%)`);
});

console.log('Top Losers:');
hotStocks.losers.slice(0, 5).forEach(stock => {
  console.log(`${stock.ticker}: ${stock.company_name_jp} (${stock.price_change_percent}%)`);
});
```

## AI Analysis Integration

### 1. Generate AI Analysis

```javascript
// Generate comprehensive AI analysis
const generateAnalysis = async (ticker, analysisType = 'comprehensive', forceRefresh = false) => {
  const url = new URL(`https://api.kessan.ai/api/v1/analysis/${ticker}/generate`);
  url.searchParams.append('analysis_type', analysisType);
  url.searchParams.append('force_refresh', forceRefresh.toString());
  
  const response = await apiRequest(url, { method: 'POST' });
  
  if (!response.ok) {
    if (response.status === 429) {
      throw new Error('Analysis quota exceeded. Please upgrade your plan.');
    }
    throw new Error('Failed to generate analysis');
  }
  
  return await response.json();
};

// Usage
try {
  const analysis = await generateAnalysis('7203', 'comprehensive');
  console.log(`Analysis for ${analysis.ticker}:`);
  console.log(`Rating: ${analysis.analysis.rating}`);
  console.log(`Confidence: ${analysis.analysis.confidence}`);
  console.log(`Key Factors: ${analysis.analysis.key_factors.join(', ')}`);
  console.log(`Price Target: ¥${analysis.analysis.price_target_range.min} - ¥${analysis.analysis.price_target_range.max}`);
} catch (error) {
  console.error('Analysis failed:', error.message);
}
```

```python
# Python Example
def generate_analysis(client, ticker, analysis_type='comprehensive', force_refresh=False):
    url = f"{client.base_url}/analysis/{ticker}/generate"
    params = {
        "analysis_type": analysis_type,
        "force_refresh": force_refresh
    }
    
    response = requests.post(url, params=params, headers=client.get_headers())
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 429:
        raise Exception("Analysis quota exceeded. Please upgrade your plan.")
    else:
        raise Exception(f"Analysis failed: {response.json().get('detail', 'Unknown error')}")

# Usage
try:
    analysis = generate_analysis(client, '7203', 'comprehensive')
    print(f"Analysis for {analysis['ticker']}:")
    print(f"Rating: {analysis['analysis']['rating']}")
    print(f"Confidence: {analysis['analysis']['confidence']}")
    print(f"Key Factors: {', '.join(analysis['analysis']['key_factors'])}")
except Exception as e:
    print(f"Analysis failed: {e}")
```

### 2. Get Specific Analysis Types

```javascript
// Get short-term analysis (1-4 weeks)
const getShortTermAnalysis = async (ticker) => {
  const response = await apiRequest(`https://api.kessan.ai/api/v1/analysis/${ticker}/short-term`);
  
  if (!response.ok) {
    throw new Error('Failed to get short-term analysis');
  }
  
  return await response.json();
};

// Get mid-term analysis (1-6 months)
const getMidTermAnalysis = async (ticker) => {
  const response = await apiRequest(`https://api.kessan.ai/api/v1/analysis/${ticker}/mid-term`);
  
  if (!response.ok) {
    throw new Error('Failed to get mid-term analysis');
  }
  
  return await response.json();
};

// Get long-term analysis (1+ years)
const getLongTermAnalysis = async (ticker) => {
  const response = await apiRequest(`https://api.kessan.ai/api/v1/analysis/${ticker}/long-term`);
  
  if (!response.ok) {
    throw new Error('Failed to get long-term analysis');
  }
  
  return await response.json();
};

// Usage - Get all analysis types for a stock
const getAllAnalyses = async (ticker) => {
  try {
    const [shortTerm, midTerm, longTerm] = await Promise.all([
      getShortTermAnalysis(ticker),
      getMidTermAnalysis(ticker),
      getLongTermAnalysis(ticker)
    ]);
    
    return {
      short_term: shortTerm,
      mid_term: midTerm,
      long_term: longTerm
    };
  } catch (error) {
    console.error('Failed to get analyses:', error.message);
    throw error;
  }
};
```

### 3. Get Analysis History

```javascript
// Get analysis history for tracking performance
const getAnalysisHistory = async (ticker, analysisType = null, limit = 10) => {
  const url = new URL(`https://api.kessan.ai/api/v1/analysis/${ticker}/history`);
  if (analysisType) {
    url.searchParams.append('analysis_type', analysisType);
  }
  url.searchParams.append('limit', limit.toString());
  
  const response = await apiRequest(url);
  
  if (!response.ok) {
    throw new Error('Failed to get analysis history');
  }
  
  return await response.json();
};

// Usage
const history = await getAnalysisHistory('7203', 'comprehensive', 5);
console.log(`Analysis history for ${history.ticker}:`);
history.analysis_history.forEach(analysis => {
  console.log(`${analysis.analysis_date}: ${analysis.result_summary} (${analysis.confidence_score})`);
});
```

## Watchlist Management

### 1. Get User Watchlist

```javascript
// Get user's watchlist with real-time prices
const getWatchlist = async () => {
  const response = await apiRequest('https://api.kessan.ai/api/v1/watchlist');
  
  if (!response.ok) {
    throw new Error('Failed to get watchlist');
  }
  
  return await response.json();
};

// Usage
const watchlist = await getWatchlist();
console.log(`You have ${watchlist.length} stocks in your watchlist:`);
watchlist.forEach(stock => {
  console.log(`${stock.ticker}: ¥${stock.current_price} (${stock.price_change_percent}%)`);
});
```

### 2. Add Stock to Watchlist

```javascript
// Add stock to watchlist
const addToWatchlist = async (ticker, notes = '') => {
  const response = await apiRequest('https://api.kessan.ai/api/v1/watchlist', {
    method: 'POST',
    body: JSON.stringify({
      ticker: ticker,
      notes: notes
    })
  });
  
  if (!response.ok) {
    if (response.status === 409) {
      throw new Error('Stock already in watchlist');
    }
    throw new Error('Failed to add stock to watchlist');
  }
  
  return await response.json();
};

// Usage
try {
  const result = await addToWatchlist('7203', 'Toyota - automotive leader');
  console.log('Stock added to watchlist:', result.ticker);
} catch (error) {
  console.error('Error:', error.message);
}
```

### 3. Update Watchlist Stock

```javascript
// Update notes for a stock in watchlist
const updateWatchlistStock = async (ticker, notes) => {
  const response = await apiRequest(`https://api.kessan.ai/api/v1/watchlist/${ticker}`, {
    method: 'PUT',
    body: JSON.stringify({
      notes: notes
    })
  });
  
  if (!response.ok) {
    throw new Error('Failed to update watchlist stock');
  }
  
  return await response.json();
};
```

### 4. Remove from Watchlist

```javascript
// Remove stock from watchlist
const removeFromWatchlist = async (ticker) => {
  const response = await apiRequest(`https://api.kessan.ai/api/v1/watchlist/${ticker}`, {
    method: 'DELETE'
  });
  
  if (!response.ok) {
    throw new Error('Failed to remove stock from watchlist');
  }
  
  return true;
};
```

### 5. Bulk Operations

```javascript
// Add multiple stocks to watchlist
const bulkAddToWatchlist = async (tickers) => {
  const response = await apiRequest('https://api.kessan.ai/api/v1/watchlist/bulk-add', {
    method: 'POST',
    body: JSON.stringify(tickers)
  });
  
  if (!response.ok) {
    throw new Error('Failed to bulk add stocks');
  }
  
  return await response.json();
};

// Remove multiple stocks from watchlist
const bulkRemoveFromWatchlist = async (tickers) => {
  const response = await apiRequest('https://api.kessan.ai/api/v1/watchlist/bulk-remove', {
    method: 'DELETE',
    body: JSON.stringify(tickers)
  });
  
  if (!response.ok) {
    throw new Error('Failed to bulk remove stocks');
  }
  
  return await response.json();
};

// Usage
const nikkei225Tickers = ['7203', '9984', '6758', '8306', '9432'];
await bulkAddToWatchlist(nikkei225Tickers);
```

## Subscription Management

### 1. Get Available Plans

```javascript
// Get all subscription plans
const getSubscriptionPlans = async () => {
  const response = await fetch('https://api.kessan.ai/api/v1/subscription/plans');
  
  if (!response.ok) {
    throw new Error('Failed to get subscription plans');
  }
  
  return await response.json();
};

// Usage
const plans = await getSubscriptionPlans();
plans.data.forEach(plan => {
  console.log(`${plan.plan_name}: ¥${plan.price_monthly}/month`);
  console.log(`- API calls: ${plan.api_quota_daily}/day`);
  console.log(`- AI analyses: ${plan.ai_analysis_quota_daily}/day`);
});
```

### 2. Get User Subscription

```javascript
// Get current user's subscription
const getMySubscription = async () => {
  const response = await apiRequest('https://api.kessan.ai/api/v1/subscription/my-subscription');
  
  if (!response.ok) {
    throw new Error('Failed to get subscription');
  }
  
  return await response.json();
};

// Usage
const subscription = await getMySubscription();
console.log(`Current plan: ${subscription.data.plan.plan_name}`);
console.log(`Status: ${subscription.data.status}`);
console.log(`API usage today: ${subscription.data.usage_quota.api_usage_today}/${subscription.data.usage_quota.api_quota_daily}`);
console.log(`AI analysis usage today: ${subscription.data.usage_quota.ai_analysis_usage_today}/${subscription.data.usage_quota.ai_analysis_quota_daily}`);
```

### 3. Upgrade Subscription

```javascript
// Upgrade to a higher plan
const upgradeSubscription = async (planId) => {
  const response = await apiRequest('https://api.kessan.ai/api/v1/subscription/upgrade', {
    method: 'POST',
    body: JSON.stringify({
      plan_id: planId
    })
  });
  
  if (!response.ok) {
    throw new Error('Failed to upgrade subscription');
  }
  
  return await response.json();
};

// Usage
try {
  const result = await upgradeSubscription(2); // Upgrade to Pro plan
  console.log('Subscription upgraded successfully');
} catch (error) {
  console.error('Upgrade failed:', error.message);
}
```

### 4. Check Quota Availability

```javascript
// Check if user has quota available
const checkQuota = async (quotaType) => {
  const response = await apiRequest(`https://api.kessan.ai/api/v1/subscription/quota/check/${quotaType}`);
  
  if (!response.ok) {
    throw new Error('Failed to check quota');
  }
  
  return await response.json();
};

// Usage
const apiQuota = await checkQuota('api');
const aiQuota = await checkQuota('ai_analysis');

if (!apiQuota.data.has_quota) {
  console.log('API quota exceeded. Consider upgrading your plan.');
}

if (!aiQuota.data.has_quota) {
  console.log('AI analysis quota exceeded. Consider upgrading your plan.');
}
```

## Error Handling

### Comprehensive Error Handling

```javascript
// Error handling utility
class KessanAPIError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = 'KessanAPIError';
    this.status = status;
    this.details = details;
  }
}

const handleAPIResponse = async (response) => {
  if (response.ok) {
    return await response.json();
  }
  
  let errorData;
  try {
    errorData = await response.json();
  } catch {
    errorData = { detail: 'Unknown error occurred' };
  }
  
  switch (response.status) {
    case 400:
      throw new KessanAPIError('Bad Request: ' + errorData.detail, 400, errorData);
    case 401:
      throw new KessanAPIError('Unauthorized: Please login again', 401, errorData);
    case 403:
      throw new KessanAPIError('Forbidden: Insufficient permissions', 403, errorData);
    case 404:
      throw new KessanAPIError('Not Found: ' + errorData.detail, 404, errorData);
    case 429:
      throw new KessanAPIError('Rate limit exceeded: ' + errorData.detail, 429, errorData);
    case 500:
      throw new KessanAPIError('Server Error: Please try again later', 500, errorData);
    default:
      throw new KessanAPIError('API Error: ' + errorData.detail, response.status, errorData);
  }
};

// Usage with error handling
const safeAPICall = async (apiFunction, ...args) => {
  try {
    return await apiFunction(...args);
  } catch (error) {
    if (error instanceof KessanAPIError) {
      console.error(`API Error (${error.status}): ${error.message}`);
      
      // Handle specific error types
      switch (error.status) {
        case 401:
          // Redirect to login
          window.location.href = '/login';
          break;
        case 429:
          // Show upgrade prompt
          showUpgradePrompt();
          break;
        case 500:
          // Show retry option
          showRetryOption();
          break;
      }
    } else {
      console.error('Unexpected error:', error.message);
    }
    throw error;
  }
};
```

## Rate Limiting

### Handling Rate Limits

```javascript
// Rate limit aware request wrapper
class RateLimitedClient {
  constructor() {
    this.requestQueue = [];
    this.isProcessing = false;
    this.rateLimitInfo = {
      limit: null,
      remaining: null,
      reset: null
    };
  }
  
  async makeRequest(url, options = {}) {
    return new Promise((resolve, reject) => {
      this.requestQueue.push({ url, options, resolve, reject });
      this.processQueue();
    });
  }
  
  async processQueue() {
    if (this.isProcessing || this.requestQueue.length === 0) {
      return;
    }
    
    this.isProcessing = true;
    
    while (this.requestQueue.length > 0) {
      // Check if we need to wait for rate limit reset
      if (this.rateLimitInfo.remaining === 0 && this.rateLimitInfo.reset) {
        const waitTime = this.rateLimitInfo.reset - Date.now();
        if (waitTime > 0) {
          console.log(`Rate limit exceeded. Waiting ${waitTime}ms...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
        }
      }
      
      const { url, options, resolve, reject } = this.requestQueue.shift();
      
      try {
        const response = await fetch(url, options);
        
        // Update rate limit info from headers
        this.updateRateLimitInfo(response);
        
        const data = await handleAPIResponse(response);
        resolve(data);
        
        // Add small delay between requests to be respectful
        await new Promise(resolve => setTimeout(resolve, 100));
        
      } catch (error) {
        reject(error);
      }
    }
    
    this.isProcessing = false;
  }
  
  updateRateLimitInfo(response) {
    const limit = response.headers.get('X-RateLimit-Limit');
    const remaining = response.headers.get('X-RateLimit-Remaining');
    const reset = response.headers.get('X-RateLimit-Reset');
    
    if (limit) this.rateLimitInfo.limit = parseInt(limit);
    if (remaining) this.rateLimitInfo.remaining = parseInt(remaining);
    if (reset) this.rateLimitInfo.reset = parseInt(reset) * 1000; // Convert to milliseconds
  }
}

// Usage
const rateLimitedClient = new RateLimitedClient();

// Make multiple requests without worrying about rate limits
const promises = ['7203', '9984', '6758'].map(ticker => 
  rateLimitedClient.makeRequest(`https://api.kessan.ai/api/v1/stocks/${ticker}`)
);

const stockDetails = await Promise.all(promises);
```

## SDKs and Libraries

### JavaScript/TypeScript SDK

```typescript
// TypeScript SDK Example
interface KessanConfig {
  baseUrl?: string;
  apiKey?: string;
  timeout?: number;
}

interface StockSearchOptions {
  query: string;
  limit?: number;
  includeInactive?: boolean;
}

interface AnalysisOptions {
  analysisType?: 'short_term' | 'mid_term' | 'long_term' | 'comprehensive';
  forceRefresh?: boolean;
}

class KessanSDK {
  private baseUrl: string;
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  
  constructor(config: KessanConfig = {}) {
    this.baseUrl = config.baseUrl || 'https://api.kessan.ai/api/v1';
  }
  
  // Authentication methods
  async login(email: string, password: string): Promise<void> {
    const response = await this.request('/auth/login', {
      method: 'POST',
      body: { email, password }
    });
    
    this.accessToken = response.data.access_token;
    this.refreshToken = response.data.refresh_token;
  }
  
  // Stock methods
  async searchStocks(options: StockSearchOptions) {
    return this.request('/stocks/search', {
      method: 'GET',
      params: options
    });
  }
  
  async getStock(ticker: string) {
    return this.request(`/stocks/${ticker}`);
  }
  
  async getPriceHistory(ticker: string, period: string = '1y', interval: string = '1d') {
    return this.request(`/stocks/${ticker}/price-history`, {
      params: { period, interval }
    });
  }
  
  // AI Analysis methods
  async generateAnalysis(ticker: string, options: AnalysisOptions = {}) {
    return this.request(`/analysis/${ticker}/generate`, {
      method: 'POST',
      params: {
        analysis_type: options.analysisType || 'comprehensive',
        force_refresh: options.forceRefresh || false
      }
    });
  }
  
  // Watchlist methods
  async getWatchlist() {
    return this.request('/watchlist');
  }
  
  async addToWatchlist(ticker: string, notes?: string) {
    return this.request('/watchlist', {
      method: 'POST',
      body: { ticker, notes }
    });
  }
  
  // Private helper methods
  private async request(endpoint: string, options: any = {}) {
    const url = new URL(endpoint, this.baseUrl);
    
    if (options.params) {
      Object.keys(options.params).forEach(key => {
        url.searchParams.append(key, options.params[key]);
      });
    }
    
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    if (this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }
    
    const response = await fetch(url.toString(), {
      method: options.method || 'GET',
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined
    });
    
    if (response.status === 401 && this.refreshToken) {
      // Try to refresh token
      await this.refreshAccessToken();
      // Retry original request
      headers.Authorization = `Bearer ${this.accessToken}`;
      return fetch(url.toString(), {
        method: options.method || 'GET',
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined
      }).then(handleAPIResponse);
    }
    
    return handleAPIResponse(response);
  }
  
  private async refreshAccessToken() {
    const response = await fetch(`${this.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.refreshToken}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      this.accessToken = data.data.access_token;
    } else {
      // Refresh failed, clear tokens
      this.accessToken = null;
      this.refreshToken = null;
      throw new Error('Session expired. Please login again.');
    }
  }
}

// Usage
const kessan = new KessanSDK();

// Login
await kessan.login('user@example.com', 'password');

// Search stocks
const searchResults = await kessan.searchStocks({ query: 'toyota', limit: 10 });

// Get stock details
const toyotaStock = await kessan.getStock('7203');

// Generate analysis
const analysis = await kessan.generateAnalysis('7203', { 
  analysisType: 'comprehensive' 
});

// Add to watchlist
await kessan.addToWatchlist('7203', 'Toyota - automotive leader');
```

This integration guide provides comprehensive examples for all major API functionality. Developers can use these examples as starting points for their own integrations with the Project Kessan API.