from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.routers import auth, projects, compositions, assets, renders, agent
from app.database import get_db, list_tables
from app import config  # loads .env at startup
import logging
import os
import shutil

logger = logging.getLogger(__name__)

app = FastAPI(title="ClipWorks API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("data/assets", exist_ok=True)

# Copy bundled seed assets into the runtime static directory so that the
# placeholder video / poster / rendered index.html are available even though
# data/ is gitignored.
_seed_assets_dir = os.path.join(os.path.dirname(__file__), "..", "seed_assets")
if os.path.isdir(_seed_assets_dir):
    shutil.copytree(_seed_assets_dir, "data/assets", dirs_exist_ok=True)

app.mount("/api/static", StaticFiles(directory="data/assets"), name="static")

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(compositions.router)
app.include_router(assets.router)
app.include_router(renders.router)
app.include_router(agent.router)


@app.on_event("startup")
def startup_event():
    logger.info("Renderer URL: %s", config.RENDERER_URL)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        tables = list_tables(connection=db.connection())
        return {"status": "ok", "tables": tables}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")
