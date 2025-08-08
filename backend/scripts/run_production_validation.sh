#!/bin/bash

# Production Data Seeding and Validation Script
# This script runs the complete production validation process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}🚀 Starting Production Data Seeding and Validation${NC}"
echo "=================================================="

# Check if we're in the correct directory
if [ ! -f "$BACKEND_DIR/requirements.txt" ]; then
    echo -e "${RED}❌ Error: Not in backend directory. Please run from backend folder.${NC}"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}⚠️  Warning: No virtual environment detected. Attempting to activate...${NC}"
    
    # Try to activate virtual environment
    if [ -d "$BACKEND_DIR/venv" ]; then
        source "$BACKEND_DIR/venv/bin/activate"
        echo -e "${GREEN}✅ Virtual environment activated${NC}"
    else
        echo -e "${RED}❌ Error: Virtual environment not found. Please create and activate venv first.${NC}"
        echo "Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        exit 1
    fi
fi

# Check required environment variables
echo -e "${BLUE}🔍 Checking environment variables...${NC}"

required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "GOOGLE_API_KEY"
    "ALPHA_VANTAGE_API_KEY"
    "NEWS_API_KEY"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    else
        echo -e "${GREEN}✅ $var is set${NC}"
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo -e "${RED}❌ Missing required environment variables:${NC}"
    for var in "${missing_vars[@]}"; do
        echo -e "${RED}   - $var${NC}"
    done
    echo -e "${YELLOW}💡 Please set these variables in your .env file or environment${NC}"
    exit 1
fi

# Check database connectivity
echo -e "${BLUE}🗄️  Checking database connectivity...${NC}"
python -c "
import sys
sys.path.append('$BACKEND_DIR')
from app.core.database import SessionLocal
try:
    db = SessionLocal()
    db.execute('SELECT 1')
    db.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Database connectivity check failed${NC}"
    exit 1
fi

# Check Redis connectivity
echo -e "${BLUE}🔴 Checking Redis connectivity...${NC}"
python -c "
import sys
import os
import redis
try:
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
    r = redis.from_url(redis_url)
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Redis connectivity check failed${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$BACKEND_DIR/logs"

# Set Python path
export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

# Run the production validation
echo -e "${BLUE}🎯 Running production data seeding and validation...${NC}"
echo "This may take several minutes..."

cd "$BACKEND_DIR"

# Run the validation script with timeout
timeout 1800 python scripts/production_data_seeding.py 2>&1 | tee logs/production_validation_$(date +%Y%m%d_%H%M%S).log

validation_exit_code=$?

# Check the exit code and provide appropriate feedback
case $validation_exit_code in
    0)
        echo -e "${GREEN}🎉 Production validation completed successfully!${NC}"
        echo -e "${GREEN}✅ All systems are ready for production deployment${NC}"
        ;;
    1)
        echo -e "${YELLOW}⚠️  Production validation completed with warnings${NC}"
        echo -e "${YELLOW}🔍 Some components may need attention - check the report${NC}"
        ;;
    2)
        echo -e "${RED}❌ Production validation failed${NC}"
        echo -e "${RED}🚨 Critical issues found - deployment not recommended${NC}"
        ;;
    124)
        echo -e "${RED}⏰ Production validation timed out (30 minutes)${NC}"
        echo -e "${RED}🚨 Process took too long - check for hanging operations${NC}"
        ;;
    *)
        echo -e "${RED}💥 Production validation crashed with unexpected error${NC}"
        echo -e "${RED}🚨 Check logs for details${NC}"
        ;;
esac

# Display report location if it exists
if [ -f "$BACKEND_DIR/production_validation_report.json" ]; then
    echo -e "${BLUE}📋 Detailed report available at:${NC}"
    echo "   $BACKEND_DIR/production_validation_report.json"
fi

# Display log location
latest_log=$(ls -t "$BACKEND_DIR/logs/production_validation_"*.log 2>/dev/null | head -n1)
if [ -n "$latest_log" ]; then
    echo -e "${BLUE}📝 Validation log available at:${NC}"
    echo "   $latest_log"
fi

echo ""
echo "=================================================="

# Exit with the same code as the validation script
exit $validation_exit_code