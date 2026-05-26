# Notes API v2 — With Database, Auth & Migrations

A production-ready REST API for managing notes, built with FastAPI.

## What's New in v2
- **PostgreSQL/SQLite** database (replaces in-memory storage)
- **Schema migrations** (versioned, up/down SQL files)
- **User registration & login** with bcrypt password hashing
- **JWT authentication** middleware on all note endpoints
- **Resource ownership** — users can only access their own notes

## Project Structure
```
notes-api-v2/
├── main.py              # FastAPI app with all endpoints
├── database.py          # Database connection layer
├── auth.py              # Password hashing, JWT, auth middleware
├── migrate.py           # Migration runner
├── requirements.txt     # Python dependencies
├── notes.db             # SQLite database (auto-created)
└── migrations/
    ├── 001_create_users_table.sql
    ├── 002_create_notes_table.sql
    └── 003_create_migrations_tracker.sql
```

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations (creates database tables)
python migrate.py

# 4. Start the server
uvicorn main:app --reload
```

## API Endpoints

### Auth (Public)
| Method | Endpoint          | Description         |
|--------|-------------------|---------------------|
| POST   | `/auth/register`  | Create a new user   |
| POST   | `/auth/login`     | Login, get JWT token|

### Notes (Protected — requires Bearer token)
| Method | Endpoint         | Description              |
|--------|------------------|--------------------------|
| POST   | `/notes`         | Create a note            |
| GET    | `/notes`         | List your notes          |
| GET    | `/notes/{id}`    | Get one of your notes    |
| PATCH  | `/notes/{id}`    | Partially update         |
| PUT    | `/notes/{id}`    | Fully replace            |
| DELETE | `/notes/{id}`    | Delete your note         |

## Example Usage

### 1. Register
```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "fashina", "email": "fash@email.com", "password": "mypassword123"}'
```

### 2. Login (get your token)
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "fashina", "password": "mypassword123"}'
```
Response: `{"access_token": "eyJhbGciOi...", "token_type": "bearer"}`

### 3. Create a note (use the token)
```bash
curl -X POST http://localhost:8000/notes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"title": "My Note", "body": "Hello world!", "tag": "general"}'
```

### 4. List your notes
```bash
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  "http://localhost:8000/notes?page=1&limit=10"
```

## Switching to PostgreSQL

1. Install PostgreSQL and create a database
2. In `database.py`, replace the SQLite connection with:
```python
import psycopg2

def get_connection():
    conn = psycopg2.connect("dbname=notesdb user=notesuser password=notespass host=localhost")
    return conn
```
3. Update SQL placeholders from `?` to `%s` (PostgreSQL syntax)
4. Run `python migrate.py` to create tables in PostgreSQL
