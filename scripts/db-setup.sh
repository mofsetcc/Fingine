#!/bin/bash

# Database setup script for Project Kessan

set -e

echo "🗄️ Setting up Project Kessan database..."

# Check if Docker services are running
if ! docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "🐳 Starting Docker services..."
    docker-compose -f docker-compose.dev.yml up -d
    echo "⏳ Waiting for database to be ready..."
    sleep 10
fi

# Check database connection
echo "🔍 Checking database connection..."
docker-compose -f docker-compose.dev.yml exec postgres pg_isready -U kessan_user -d kessan_dev

if [ $? -eq 0 ]; then
    echo "✅ Database is ready"
else
    echo "❌ Database is not ready. Please check Docker services."
    exit 1
fi

# Navigate to backend directory
cd backend

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "🐍 Activating Python virtual environment..."
    source venv/bin/activate
else
    echo "❌ Python virtual environment not found. Please run ./scripts/dev-setup.sh first."
    exit 1
fi

# Run database migrations
echo "🔄 Running database migrations..."
python -c "
import asyncio
import sys
sys.path.append('.')

from alembic import command
from alembic.config import Config

# Create Alembic config
alembic_cfg = Config('alembic.ini')

# Run upgrade
try:
    command.upgrade(alembic_cfg, 'head')
    print('✅ Database migrations completed successfully')
except Exception as e:
    print(f'❌ Migration failed: {e}')
    sys.exit(1)
"

# Initialize database with default data
echo "📦 Initializing database with default data..."
python -c "
import asyncio
import sys
sys.path.append('.')

from app.core.init_db import init_db

try:
    asyncio.run(init_db())
except Exception as e:
    print(f'❌ Database initialization failed: {e}')
    sys.exit(1)
"

echo "✅ Database setup completed successfully!"
echo ""
echo "🌐 Database access:"
echo "- PostgreSQL: localhost:5432"
echo "- Database: kessan_dev"
echo "- Username: kessan_user"
echo "- PgAdmin: http://localhost:8080 (admin@kessan.com / admin)"