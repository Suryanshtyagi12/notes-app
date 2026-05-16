# Notes REST API

A production-ready Notes REST API built with **FastAPI**, **SQLAlchemy (sync)**, and **PostgreSQL**.

## Features

- 🔐 **JWT Authentication** — Register, login, and access protected routes via Bearer tokens
- 📝 **Full Notes CRUD** — Create, read, update, delete your notes
- 📌 **Pin Notes** — Toggle pinned state; pinned notes surface first in lists
- 🤝 **Note Sharing** — Share any note with other registered users by email; revoke anytime
- 🗄️ **PostgreSQL** with UUID primary keys on every table

---

## Project Structure

```
notes-app/
├── main.py          # FastAPI app, router registration, DB init
├── database.py      # SQLAlchemy engine, SessionLocal, Base, get_db
├── models.py        # ORM models: User, Note, NoteShare
├── schemas.py       # Pydantic v2 request / response schemas
├── auth.py          # JWT helpers, bcrypt, get_current_user dependency
├── routes/
│   ├── __init__.py
│   ├── users.py     # POST /auth/register, POST /auth/login, GET /auth/me
│   └── notes.py     # CRUD /notes + /notes/{id}/share
├── .env             # DATABASE_URL, SECRET_KEY  ← never commit this
└── requirements.txt
```

---

## Setup

### 1. Create & activate virtual environment

```bash
# Create
python -m venv venv

# Activate — Linux / macOS
source venv/bin/activate

# Activate — Windows
venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose passlib[bcrypt] python-dotenv "pydantic[email]"
```

### 3. Freeze requirements

```bash
pip freeze > requirements.txt
```

### 4. Configure `.env`

```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
SECRET_KEY=your-very-secret-key
```

### 5. Run the server

```bash
uvicorn main:app --reload
```

Interactive docs available at **http://127.0.0.1:8000/docs**

---

## API Endpoints

### Authentication

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login → receive JWT token |
| GET | `/auth/me` | Get current user profile |

### Notes

| Method | Path | Description |
|--------|------|-------------|
| POST | `/notes/` | Create a note |
| GET | `/notes/` | List owned + shared notes |
| GET | `/notes/{id}` | Get a specific note |
| PUT | `/notes/{id}` | Update a note (owner only) |
| DELETE | `/notes/{id}` | Delete a note (owner only) |
| POST | `/notes/{id}/share` | Share note by email (owner only) |
| DELETE | `/notes/{id}/share/{user_id}` | Revoke a share (owner only) |

---

## Auth Flow

1. `POST /auth/register` with `{ "email": "...", "password": "..." }`
2. `POST /auth/login` with form fields `username` + `password` → receive `access_token`
3. Include `Authorization: Bearer <access_token>` on all protected requests

---

## Tech Stack

- **FastAPI** — Modern async Python web framework
- **SQLAlchemy** — Sync ORM for PostgreSQL
- **psycopg2-binary** — PostgreSQL adapter
- **python-jose** — JWT encoding / decoding (HS256)
- **passlib[bcrypt]** — Secure password hashing
- **python-dotenv** — Environment variable management
- **pydantic[email]** — Data validation with email support
