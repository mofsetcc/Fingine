# Project Kessan (決算) - AI-Powered Japanese Stock Analysis Platform

An AI-powered stock trend analysis platform tailored for the Japanese market, providing retail investors and small-to-medium financial institutions with institutional-grade investment analysis.

## Features

- **Multi-Horizon AI Analysis**: Short-term (1-4 weeks), mid-term (1-6 months), and long-term (1+ years) stock analysis
- **Real-time Data**: Stock prices, financial reports, and news sentiment from multiple sources
- **Japanese Market Focus**: Specialized for Tokyo Stock Exchange (TSE) listed companies
- **AI-Powered Insights**: Google Gemini integration for intelligent stock analysis
- **Subscription Tiers**: Free, Pro, and Business plans with different features and quotas

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PostgreSQL** - Primary database
- **Redis** - Caching and session storage
- **SQLAlchemy** - ORM
- **Celery** - Background task processing
- **Google Gemini API** - AI analysis

### Frontend
- **React 18+** with TypeScript
- **Redux Toolkit** - State management
- **Tailwind CSS** - Styling
- **TradingView Charts** - Stock visualization
- **Vite** - Build tool

### Infrastructure
- **Docker** - Containerization
- **AWS Fargate** - Container orchestration
- **AWS RDS** - Managed PostgreSQL
- **AWS ElastiCache** - Managed Redis
- **CloudFront** - CDN

## Project Structure

```
japanese-stock-analysis-platform/
├── backend/                 # FastAPI backend services
├── frontend/               # React TypeScript frontend
├── shared/                 # Shared types and utilities
├── docker/                 # Docker configurations
├── docs/                   # Documentation
├── scripts/               # Development and deployment scripts
└── .kiro/                 # Kiro spec files
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. Clone the repository
2. Set up backend environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up frontend environment:
   ```bash
   cd frontend
   npm install
   ```

4. Start local services:
   ```bash
   docker-compose -f docker-compose.dev.yml up -d
   ```

5. Run database migrations:
   ```bash
   cd backend
   alembic upgrade head
   ```

6. Start development servers:
   ```bash
   # Backend (Terminal 1)
   cd backend
   uvicorn app.main:app --reload

   # Frontend (Terminal 2)
   cd frontend
   npm start
   ```

## API Documentation

Once the backend is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Environment Variables

Copy `.env.example` to `.env` and configure:
- Database connection
- Redis connection
- API keys (Alpha Vantage, Google Gemini, News API)
- OAuth credentials (Google, LINE)

## License

MIT License - see LICENSE file for details.# Fingine
