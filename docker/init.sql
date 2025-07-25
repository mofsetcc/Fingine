-- Initialize database for Project Kessan development
-- This script runs when the PostgreSQL container starts for the first time

-- Create additional databases for testing
CREATE DATABASE kessan_test;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE kessan_dev TO kessan_user;
GRANT ALL PRIVILEGES ON DATABASE kessan_test TO kessan_user;

-- Create extensions
\c kessan_dev;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

\c kessan_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";