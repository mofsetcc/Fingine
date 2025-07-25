#!/bin/bash

# Start development servers for Project Kessan

set -e

echo "🚀 Starting Project Kessan development servers..."

# Function to run commands in new terminal tabs (macOS)
run_in_new_tab() {
    osascript -e "tell application \"Terminal\" to do script \"cd $(pwd) && $1\""
}

# Start Docker services if not running
echo "🐳 Checking Docker services..."
if ! docker-compose -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo "Starting Docker services..."
    docker-compose -f docker-compose.dev.yml up -d
    sleep 5
fi

# Start backend in new terminal tab
echo "🐍 Starting backend server..."
run_in_new_tab "cd backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

# Start frontend in new terminal tab
echo "⚛️ Starting frontend server..."
run_in_new_tab "cd frontend && npm run dev"

echo "✅ Development servers started!"
echo ""
echo "🌐 Access points:"
echo "- Frontend: http://localhost:3000"
echo "- Backend API: http://localhost:8000"
echo "- API Docs: http://localhost:8000/docs"
echo "- PgAdmin: http://localhost:8080"