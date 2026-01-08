-- PostgreSQL Initialization Script
-- This script runs when the PostgreSQL container is first created

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS retail;

-- Grant permissions
GRANT ALL ON SCHEMA retail TO retail_admin;
GRANT ALL ON SCHEMA public TO retail_admin;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'RetailPro ERP database initialized successfully';
END $$;
