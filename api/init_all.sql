-- Master Initialization Script
-- This script is run as the 'postgres' superuser to set up the role and database.

-- 1. Create Role
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'smart_user') THEN
        CREATE ROLE smart_user WITH LOGIN PASSWORD 'smart_pass';
    END IF;
END
$$;

ALTER ROLE smart_user SUPERUSER;

-- 2. Create Database
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_database WHERE datname = 'smart_task_hub') THEN
        CREATE DATABASE smart_task_hub OWNER smart_user;
    END IF;
END
$$;

ALTER DATABASE smart_task_hub OWNER TO smart_user;
GRANT ALL PRIVILEGES ON DATABASE smart_task_hub TO smart_user;

-- 3. Connect to the database and run schema
\c smart_task_hub
-- Note: /app is the root of the project inside the container
\i /app/init_smart_task.sql
