-- Migration 002: Create Notes Table
-- Description: Sets up the notes table with a foreign key to users

-- ============ UP ============

CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    tag VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_notes_user_id ON notes(user_id);

CREATE INDEX IF NOT EXISTS idx_notes_created_at ON notes(created_at);

-- ============ DOWN ============
-- DROP INDEX IF EXISTS idx_notes_created_at;
-- DROP INDEX IF EXISTS idx_notes_user_id;
-- DROP TABLE IF EXISTS notes;
