"""
Notes API v2 — Production-Ready
=================================
Features:
1. PostgreSQL database with versioned schema migrations
2. User registration & login with bcrypt password hashing
3. JWT middleware protecting all note endpoints
4. Resource ownership — users can only access their own notes

Run migrations first:  python migrate.py
Start the server:      uvicorn main:app --reload
"""

import time
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Depends, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, Field, field_validator

from database import query
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("notes_api")

app = FastAPI(
    title="Notes API v2",
    description="Notes API with PostgreSQL, JWT Auth, Migrations, and Resource Ownership.",
    version="2.0.0",
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration_ms:.1f}ms)")
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for error in exc.errors():
        field = " → ".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({"field": field, "message": error["msg"]})
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation failed", "errors": errors},
    )


# ── Auth Models ───────────────────────────────
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace("_", "").isalnum():
            raise ValueError("Username must contain only letters, numbers, and underscores")
        return v.strip().lower()

    @field_validator("email")
    @classmethod
    def email_must_contain_at(cls, v):
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email format")
        return v.strip().lower()


class UserLogin(BaseModel):
    username: str
    password: str


# ── Note Models ───────────────────────────────
class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=10000)
    tag: Optional[str] = Field(None, max_length=50)

    @field_validator("title", "body")
    @classmethod
    def must_not_be_blank(cls, v, info):
        if not v.strip():
            raise ValueError(f"{info.field_name} must not be blank")
        return v.strip()


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    body: Optional[str] = Field(None, min_length=1, max_length=10000)
    tag: Optional[str] = Field(None, max_length=50)

    @field_validator("title", "body")
    @classmethod
    def must_not_be_blank(cls, v, info):
        if v is not None and not v.strip():
            raise ValueError(f"{info.field_name} must not be blank")
        return v.strip() if v else v


# ══════════════════════════════════════════════
#  AUTH ENDPOINTS
# ══════════════════════════════════════════════

@app.post("/auth/register", status_code=201)
def register(user: UserRegister):
    existing = query(
        "SELECT id FROM users WHERE username = %s",
        (user.username,),
        fetch_one=True,
    )
    if existing:
        raise HTTPException(status_code=400, detail="Username already taken")

    existing_email = query(
        "SELECT id FROM users WHERE email = %s",
        (user.email,),
        fetch_one=True,
    )
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed = hash_password(user.password)

    user_id = query(
        "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
        (user.username, user.email, hashed),
    )

    return {
        "message": "User registered successfully",
        "user": {"id": user_id, "username": user.username, "email": user.email},
    }


@app.post("/auth/login")
def login(credentials: UserLogin):
    user = query(
        "SELECT id, username, password_hash FROM users WHERE username = %s",
        (credentials.username,),
        fetch_one=True,
    )

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = create_access_token(user_id=user["id"], username=user["username"])

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
    }


# ══════════════════════════════════════════════
#  NOTE ENDPOINTS (Protected)
# ══════════════════════════════════════════════

@app.post("/notes", status_code=201)
def create_note(note: NoteCreate, user: dict = Depends(get_current_user)):
    user_id = int(user["sub"])
    now = datetime.now(timezone.utc).isoformat()

    note_id = query(
        """INSERT INTO notes (user_id, title, body, tag, created_at, updated_at)
           VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
        (user_id, note.title, note.body, note.tag, now, now),
    )

    return {
        "id": note_id,
        "user_id": user_id,
        "title": note.title,
        "body": note.body,
        "tag": note.tag,
        "created_at": now,
        "updated_at": now,
    }


@app.get("/notes")
def list_notes(
    user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    order: str = Query("desc"),
):
    user_id = int(user["sub"])

    sql = "SELECT * FROM notes WHERE user_id = %s"
    params = [user_id]

    if tag:
        sql += " AND tag = %s"
        params.append(tag)

    if search:
        sql += " AND (title LIKE %s OR body LIKE %s)"
        search_pattern = f"%{search}%"
        params.extend([search_pattern, search_pattern])

    allowed_sort = {"created_at", "updated_at", "title"}
    if sort_by not in allowed_sort:
        sort_by = "created_at"
    sort_order = "ASC" if order.lower() == "asc" else "DESC"
    sql += f" ORDER BY {sort_by} {sort_order}"

    count_sql = sql.replace("SELECT *", "SELECT COUNT(*) as count", 1)
    count_sql = count_sql.split(" ORDER BY")[0]
    total_result = query(count_sql, tuple(params), fetch_one=True)
    total = total_result["count"] if total_result else 0

    offset = (page - 1) * limit
    sql += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])

    notes = query(sql, tuple(params), fetch_all=True)

    return {
        "data": notes,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": max(1, -(-total // limit)),
        },
    }


@app.get("/notes/{note_id}")
def get_note(note_id: int, user: dict = Depends(get_current_user)):
    user_id = int(user["sub"])

    note = query(
        "SELECT * FROM notes WHERE id = %s AND user_id = %s",
        (note_id, user_id),
        fetch_one=True,
    )

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return note


@app.patch("/notes/{note_id}")
def update_note(note_id: int, updates: NoteUpdate, user: dict = Depends(get_current_user)):
    user_id = int(user["sub"])

    existing = query(
        "SELECT * FROM notes WHERE id = %s AND user_id = %s",
        (note_id, user_id),
        fetch_one=True,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    update_data = updates.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=422, detail="No fields provided to update")

    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()

    set_clause = ", ".join(f"{key} = %s" for key in update_data.keys())
    values = list(update_data.values()) + [note_id, user_id]

    query(
        f"UPDATE notes SET {set_clause} WHERE id = %s AND user_id = %s",
        tuple(values),
    )

    return query("SELECT * FROM notes WHERE id = %s", (note_id,), fetch_one=True)


@app.put("/notes/{note_id}")
def replace_note(note_id: int, note: NoteCreate, user: dict = Depends(get_current_user)):
    user_id = int(user["sub"])

    existing = query(
        "SELECT * FROM notes WHERE id = %s AND user_id = %s",
        (note_id, user_id),
        fetch_one=True,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    now = datetime.now(timezone.utc).isoformat()
    query(
        "UPDATE notes SET title = %s, body = %s, tag = %s, updated_at = %s WHERE id = %s AND user_id = %s",
        (note.title, note.body, note.tag, now, note_id, user_id),
    )

    return query("SELECT * FROM notes WHERE id = %s", (note_id,), fetch_one=True)


@app.delete("/notes/{note_id}")
def delete_note(note_id: int, user: dict = Depends(get_current_user)):
    user_id = int(user["sub"])

    existing = query(
        "SELECT * FROM notes WHERE id = %s AND user_id = %s",
        (note_id, user_id),
        fetch_one=True,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")

    query(
        "DELETE FROM notes WHERE id = %s AND user_id = %s",
        (note_id, user_id),
    )

    return {"detail": "Note deleted successfully", "deleted": existing}


@app.get("/", tags=["Health"])
def root():
    return {"message": "Notes API v2 is running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
