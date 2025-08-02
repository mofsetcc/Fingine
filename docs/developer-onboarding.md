# Project Kessan Developer Onboarding Guide

Welcome to Project Kessan! This guide will help you get started with developing and contributing to the AI-powered Japanese stock analysis platform.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Development Environment Setup](#development-environment-setup)
3. [Architecture Overview](#architecture-overview)
4. [Development Workflow](#development-workflow)
5. [Code Standards](#code-standards)
6. [Testing Guidelines](#testing-guidelines)
7. [Deployment Process](#deployment-process)
8. [Contributing Guidelines](#contributing-guidelines)

## Project Overview

### What is Project Kessan?

Project Kessan (決算 - "Financial Results") is an AI-powered Japanese stock trend analysis platform that democratizes institutional-grade investment analysis. The platform provides:

- **AI-Powered Analysis**: Multi-horizon stock analysis using Google Gemini API
- **Real-time Data**: Live stock prices and market indices for TSE-listed companies
- **Japanese Language Support**: Native Japanese news analysis and sentiment scoring
- **Subscription Management**: Flexible pricing tiers with quota management
- **Comprehensive API**: RESTful API for third-party integrations

### Technology Stack

**Backend:**
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for multi-layer caching
- **AI/ML**: Google Gemini API, Japanese NLP models
- **Authentication**: JWT tokens with OAuth support
- **Monitoring**: Datadog APM, structured logging

**Frontend:**
- **Framework**: React 18 with TypeScript
- **State Management**: Redux Toolkit
- **UI Components**: Custom components with Tailwind CSS
- **Charts**: TradingView integration, Chart.js
- **Build Tool**: Vite

**Infrastructure:**
- **Cloud Provider**: AWS (Fargate, RDS, ElastiCache, CloudFront)
- **Containerization**: Docker with multi-stage builds
- **CI/CD**: GitHub Actions
- **Infrastructure as Code**: Terraform + CloudFormation

## Development Environment Setup

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** with pip
- **Node.js 18+** with npm/yarn
- **Docker** and Docker Compose
- **Git**
- **PostgreSQL** (for local development)
- **Redis** (for local development)

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/project-kessan.git
cd project-kessan
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env

# Edit .env file with your configuration
nano .env
```

**Required Environment Variables:**

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/kessan_dev

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# External APIs
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
GOOGLE_GEMINI_API_KEY=your-gemini-api-key
NEWS_API_KEY=your-news-api-key

# OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
LINE_CLIENT_ID=your-line-client-id
LINE_CLIENT_SECRET=your-line-client-secret

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Monitoring
DATADOG_API_KEY=your-datadog-key
DATADOG_SERVICE_NAME=kessan-api-dev
```

### 3. Database Setup

```bash
# Start PostgreSQL and Redis (using Docker)
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head

# (Optional) Populate sample data
python scripts/populate_sample_stocks.py
```

### 4. Frontend Setup

```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install

# Copy environment file
cp .env.example .env.local

# Edit environment file
nano .env.local
```

**Frontend Environment Variables:**

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_GOOGLE_CLIENT_ID=your-google-client-id
VITE_LINE_CLIENT_ID=your-line-client-id
VITE_TRADINGVIEW_WIDGET_ID=your-tradingview-widget-id
```

### 5. Start Development Servers

**Terminal 1 - Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 - Services (Optional):**
```bash
# Start all services with Docker Compose
docker-compose up -d
```

### 6. Verify Setup

1. **Backend API**: Visit http://localhost:8000/docs for Swagger documentation
2. **Frontend**: Visit http://localhost:3000 for the React application
3. **Health Check**: Visit http://localhost:8000/health for API health status

## Architecture Overview

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React SPA     │    │   API Gateway    │    │  Load Balancer  │
│   (CloudFront)  │◄──►│  (AWS Gateway)   │◄──►│   (ALB/ELB)     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │ User Service │ │Stock Service│ │ AI Service │
        │  (Fargate)   │ │  (Fargate)  │ │ (Fargate)  │
        └──────────────┘ └─────────────┘ └────────────┘
                │               │               │
        ┌───────▼──────┐ ┌──────▼──────┐ ┌─────▼──────┐
        │   Users DB   │ │  Stocks DB  │ │ Redis Cache│
        │ (RDS Postgres│ │(RDS Postgres│ │(ElastiCache│
        └──────────────┘ └─────────────┘ └────────────┘
```

### Directory Structure

```
project-kessan/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API endpoints
│   │   │   └── v1/           # API version 1
│   │   ├── core/             # Core functionality
│   │   ├── models/           # Database models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/         # Business logic
│   │   └── adapters/         # External API adapters
│   ├── alembic/              # Database migrations
│   ├── tests/                # Test files
│   └── scripts/              # Utility scripts
├── frontend/                  # React frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── pages/           # Page components
│   │   ├── store/           # Redux store
│   │   ├── types/           # TypeScript types
│   │   └── utils/           # Utility functions
│   ├── public/              # Static assets
│   └── tests/               # Frontend tests
├── infrastructure/           # Infrastructure as Code
│   ├── terraform/           # Terraform configurations
│   ├── cloudformation/      # CloudFormation templates
│   └── monitoring/          # Monitoring configurations
├── docs/                    # Documentation
│   ├── api/                # API documentation
│   └── deployment/         # Deployment guides
└── scripts/                # Project scripts
```

### Key Components

**Backend Services:**
- **Authentication Service**: User management, JWT tokens, OAuth
- **Stock Service**: Stock data, search, market indices
- **AI Analysis Service**: Gemini API integration, analysis generation
- **News Service**: News aggregation, sentiment analysis
- **Subscription Service**: Plan management, quota tracking
- **Watchlist Service**: Personal stock tracking

**Frontend Components:**
- **Dashboard**: Market overview, hot stocks, search
- **Stock Analysis**: Detailed stock view with AI insights
- **Watchlist**: Personal stock tracking interface
- **User Profile**: Account management, subscription settings
- **Authentication**: Login, registration, OAuth flows

## Development Workflow

### Git Workflow

We use **Git Flow** with the following branches:

- **main**: Production-ready code
- **develop**: Integration branch for features
- **feature/**: Feature development branches
- **hotfix/**: Critical bug fixes
- **release/**: Release preparation branches

### Branch Naming Convention

```bash
feature/JIRA-123-add-stock-search
bugfix/JIRA-456-fix-login-error
hotfix/JIRA-789-critical-security-fix
release/v1.2.0
```

### Development Process

1. **Create Feature Branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/JIRA-123-add-stock-search
   ```

2. **Develop and Test**
   ```bash
   # Make your changes
   # Run tests
   npm test                    # Frontend tests
   python -m pytest          # Backend tests
   
   # Run linting
   npm run lint               # Frontend linting
   flake8 app/               # Backend linting
   ```

3. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add stock search functionality
   
   - Implement fuzzy search for Japanese stocks
   - Add relevance scoring
   - Optimize for sub-500ms response times
   
   Closes JIRA-123"
   ```

4. **Push and Create PR**
   ```bash
   git push origin feature/JIRA-123-add-stock-search
   # Create Pull Request on GitHub
   ```

5. **Code Review and Merge**
   - Address review comments
   - Ensure CI passes
   - Merge to develop branch

### Commit Message Convention

We follow **Conventional Commits**:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
feat(api): add stock search endpoint
fix(auth): resolve JWT token expiration issue
docs: update API integration guide
test(stocks): add unit tests for stock service
```

## Code Standards

### Python Code Standards

**Style Guide**: We follow PEP 8 with some modifications:

```python
# Good: Clear function names and type hints
async def get_stock_analysis(
    ticker: str,
    analysis_type: AnalysisType,
    force_refresh: bool = False
) -> AIAnalysisResult:
    """
    Generate AI analysis for a stock.
    
    Args:
        ticker: 4-digit Japanese stock ticker
        analysis_type: Type of analysis to generate
        force_refresh: Force new analysis even if cached
        
    Returns:
        AI analysis result with rating and insights
        
    Raises:
        InvalidTickerError: If ticker format is invalid
        QuotaExceededError: If user quota is exceeded
    """
    if not is_valid_ticker(ticker):
        raise InvalidTickerError(f"Invalid ticker: {ticker}")
    
    # Implementation...
```

**Key Principles:**
- Use type hints for all function parameters and return values
- Write comprehensive docstrings
- Handle errors explicitly with custom exceptions
- Use async/await for I/O operations
- Follow dependency injection patterns

### TypeScript Code Standards

**Style Guide**: We use ESLint with TypeScript-specific rules:

```typescript
// Good: Proper typing and error handling
interface StockSearchProps {
  onStockSelect: (stock: Stock) => void;
  placeholder?: string;
  maxResults?: number;
}

const StockSearch: React.FC<StockSearchProps> = ({
  onStockSelect,
  placeholder = "Search stocks...",
  maxResults = 20
}) => {
  const [query, setQuery] = useState<string>('');
  const [results, setResults] = useState<Stock[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await stockAPI.search({
        query: searchQuery,
        limit: maxResults
      });
      setResults(response.results);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setIsLoading(false);
    }
  }, [maxResults]);

  // Component implementation...
};
```

**Key Principles:**
- Use strict TypeScript configuration
- Define interfaces for all props and data structures
- Handle loading and error states explicitly
- Use React hooks properly (useCallback, useMemo for optimization)
- Follow component composition patterns

### Database Standards

**Migration Naming:**
```
001_initial_database_schema.py
002_add_search_optimization_indexes.py
003_add_query_optimization_indexes.py
```

**Model Conventions:**
```python
class Stock(Base):
    __tablename__ = "stocks"
    
    ticker = Column(String(10), primary_key=True)
    company_name_jp = Column(String(255), nullable=False)
    company_name_en = Column(String(255))
    sector_jp = Column(String(100))
    industry_jp = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_stocks_company_name_jp', 'company_name_jp'),
        Index('idx_stocks_sector_industry', 'sector_jp', 'industry_jp'),
        Index('idx_stocks_active', 'is_active'),
    )
```

## Testing Guidelines

### Backend Testing

**Test Structure:**
```
tests/
├── unit/                  # Unit tests
│   ├── test_models/
│   ├── test_services/
│   └── test_utils/
├── integration/           # Integration tests
│   ├── test_api/
│   ├── test_database/
│   └── test_external_apis/
└── e2e/                  # End-to-end tests
    └── test_workflows/
```

**Unit Test Example:**
```python
import pytest
from unittest.mock import Mock, patch
from app.services.stock_service import StockService
from app.models.stock import Stock

class TestStockService:
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def stock_service(self, mock_db):
        return StockService(mock_db)
    
    async def test_search_stocks_success(self, stock_service, mock_db):
        # Arrange
        expected_stocks = [
            Stock(ticker="7203", company_name_jp="トヨタ自動車"),
            Stock(ticker="9984", company_name_jp="ソフトバンクグループ")
        ]
        mock_db.query.return_value.filter.return_value.limit.return_value.all.return_value = expected_stocks
        
        # Act
        result = await stock_service.search_stocks("toyota")
        
        # Assert
        assert len(result.results) == 2
        assert result.results[0].ticker == "7203"
        assert result.total_results == 2
    
    async def test_search_stocks_empty_query(self, stock_service):
        # Act & Assert
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await stock_service.search_stocks("")
```

**Integration Test Example:**
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

class TestStockAPI:
    def test_search_stocks_endpoint(self):
        # Act
        response = client.get("/api/v1/stocks/search?query=toyota&limit=5")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_results" in data
        assert len(data["results"]) <= 5
    
    def test_search_stocks_invalid_query(self):
        # Act
        response = client.get("/api/v1/stocks/search?query=&limit=5")
        
        # Assert
        assert response.status_code == 400
```

### Frontend Testing

**Test Structure:**
```
src/
├── components/
│   ├── StockSearch.tsx
│   └── __tests__/
│       └── StockSearch.test.tsx
├── pages/
│   ├── Dashboard.tsx
│   └── __tests__/
│       └── Dashboard.test.tsx
└── utils/
    ├── api.ts
    └── __tests__/
        └── api.test.ts
```

**Component Test Example:**
```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import StockSearch from '../StockSearch';
import { stocksSlice } from '../../store/slices/stocksSlice';

const mockStore = configureStore({
  reducer: {
    stocks: stocksSlice.reducer
  }
});

describe('StockSearch', () => {
  const mockOnStockSelect = jest.fn();

  beforeEach(() => {
    mockOnStockSelect.mockClear();
  });

  it('renders search input', () => {
    render(
      <Provider store={mockStore}>
        <StockSearch onStockSelect={mockOnStockSelect} />
      </Provider>
    );

    expect(screen.getByPlaceholderText('Search stocks...')).toBeInTheDocument();
  });

  it('calls onStockSelect when stock is clicked', async () => {
    // Mock API response
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        results: [
          { ticker: '7203', company_name_jp: 'トヨタ自動車' }
        ]
      })
    });

    render(
      <Provider store={mockStore}>
        <StockSearch onStockSelect={mockOnStockSelect} />
      </Provider>
    );

    const searchInput = screen.getByPlaceholderText('Search stocks...');
    fireEvent.change(searchInput, { target: { value: 'toyota' } });

    await waitFor(() => {
      expect(screen.getByText('トヨタ自動車')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('トヨタ自動車'));
    expect(mockOnStockSelect).toHaveBeenCalledWith({
      ticker: '7203',
      company_name_jp: 'トヨタ自動車'
    });
  });
});
```

### Running Tests

**Backend Tests:**
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=app --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_stock_service.py

# Run tests with specific marker
python -m pytest -m "not slow"
```

**Frontend Tests:**
```bash
# Run all tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- StockSearch.test.tsx
```

## Deployment Process

### Environment Overview

1. **Development**: Local development environment
2. **Staging**: Pre-production testing environment
3. **Production**: Live production environment

### CI/CD Pipeline

Our GitHub Actions pipeline includes:

1. **Code Quality Checks**
   - Linting (ESLint, Flake8)
   - Type checking (TypeScript, mypy)
   - Security scanning (Bandit, npm audit)

2. **Testing**
   - Unit tests
   - Integration tests
   - E2E tests (Playwright)

3. **Build and Deploy**
   - Docker image building
   - Infrastructure deployment (Terraform)
   - Application deployment (AWS Fargate)

### Deployment Commands

**Staging Deployment:**
```bash
# Deploy to staging
./scripts/deploy-staging.sh

# Run smoke tests
./scripts/run-smoke-tests.sh staging
```

**Production Deployment:**
```bash
# Create release branch
git checkout -b release/v1.2.0

# Update version numbers
npm version 1.2.0
# Update backend version in pyproject.toml

# Deploy to production
./scripts/deploy-production.sh

# Monitor deployment
./scripts/monitor-deployment.sh production
```

### Database Migrations

**Staging:**
```bash
# Run migrations on staging
alembic -c alembic-staging.ini upgrade head
```

**Production:**
```bash
# Run migrations on production (with backup)
./scripts/backup-production-db.sh
alembic -c alembic-production.ini upgrade head
```

## Contributing Guidelines

### Before You Start

1. **Check existing issues** on GitHub
2. **Discuss major changes** in GitHub Discussions
3. **Follow the development workflow** outlined above

### Pull Request Process

1. **Create descriptive PR title**
   ```
   feat(api): add stock news sentiment analysis
   ```

2. **Fill out PR template** with:
   - Description of changes
   - Testing performed
   - Screenshots (for UI changes)
   - Breaking changes (if any)

3. **Ensure CI passes**
   - All tests pass
   - Code coverage maintained
   - No linting errors

4. **Request review** from appropriate team members

5. **Address feedback** and update PR

6. **Squash and merge** once approved

### Code Review Guidelines

**As a Reviewer:**
- Focus on logic, performance, and maintainability
- Check for proper error handling
- Verify tests cover new functionality
- Ensure documentation is updated

**As an Author:**
- Respond to all comments
- Make requested changes or explain why not
- Keep PR scope focused and small
- Update tests and documentation

### Getting Help

- **Slack**: #kessan-dev channel
- **GitHub Discussions**: For design discussions
- **GitHub Issues**: For bug reports and feature requests
- **Documentation**: Check docs/ directory first

### Resources

- **API Documentation**: `/docs/api/`
- **Architecture Decisions**: `/docs/architecture/`
- **Deployment Guide**: `/docs/deployment/`
- **Troubleshooting**: `/docs/troubleshooting/`

Welcome to the team! 🚀