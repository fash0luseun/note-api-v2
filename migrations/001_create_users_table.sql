-- Migration 001: Create Users Table
-- Description: Sets up the users table for authentication

-- ============ UP ============

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ============ DOWN ============
-- DROP INDEX IF EXISTS idx_users_email;
-- DROP INDEX IF EXISTS idx_users_username;
-- DROP TABLE IF EXISTS users;
