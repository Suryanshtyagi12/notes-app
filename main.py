from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine
import models
from routes import notes, users


# ---------------------------------------------------------------------------
# Lifespan: create tables once at startup (no Alembic)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    yield


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Notes API",
    version="1.0.0",
    description=(
        "A JWT-authenticated REST API for managing notes with sharing and pinning support, "
        "built with FastAPI + SQLAlchemy + PostgreSQL."
    ),
    # Keep the auto-generated OpenAPI schema endpoint active (default: /openapi.json)
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow all origins for hosted deployment
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers (no extra prefix — each router defines its own prefix internally)
# ---------------------------------------------------------------------------
app.include_router(users.router)
app.include_router(notes.router)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    """Health-check — confirms the API is running."""
    return {"status": "ok", "message": "Notes API is running 🚀"}


# ---------------------------------------------------------------------------
# About — custom feature showcase
# ---------------------------------------------------------------------------
@app.get("/about", tags=["Meta"])
def about():
    """
    Returns project metadata and a description of the custom feature implemented
    beyond the base requirements.
    """
    return {
        "name": "Your Name",
        "email": "your@email.com",
        "my_features": {
            "note_pinning": (
                "Users can pin important notes via PATCH /notes/{id}/pin. "
                "Pinned notes are sorted to the top in GET /notes. "
                "I chose this because pinning is the most universally used organizational feature "
                "in note apps like Google Keep, and it required a deliberate decision about sort "
                "ordering in the list endpoint."
            )
        },
    }
