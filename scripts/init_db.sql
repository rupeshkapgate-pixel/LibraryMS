-- Library Management System - Database Initialization
-- Creates schemas for logical service separation

CREATE SCHEMA IF NOT EXISTS books_db;
CREATE SCHEMA IF NOT EXISTS members_db;
CREATE SCHEMA IF NOT EXISTS lending_db;

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA books_db TO library;
GRANT ALL PRIVILEGES ON SCHEMA members_db TO library;
GRANT ALL PRIVILEGES ON SCHEMA lending_db TO library;

GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA books_db TO library;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA members_db TO library;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA lending_db TO library;

ALTER DEFAULT PRIVILEGES IN SCHEMA books_db GRANT ALL ON TABLES TO library;
ALTER DEFAULT PRIVILEGES IN SCHEMA members_db GRANT ALL ON TABLES TO library;
ALTER DEFAULT PRIVILEGES IN SCHEMA lending_db GRANT ALL ON TABLES TO library;
