-- Migration 003: Create Migrations Tracking Table
-- Description: Tracks which migrations have been applied to this database
-- Date: 2026-05-26

-- ============ UP ============

CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(255) UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============ DOWN ============
-- DROP TABLE IF EXISTS schema_migrations;
