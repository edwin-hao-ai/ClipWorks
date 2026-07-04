from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import auth, projects, compositions, assets, renders
import os

app = FastAPI(title="ClipWorks API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("data/assets", exist_ok=True)
app.mount("/api/static", StaticFiles(directory="data/assets"), name="static")

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(compositions.router)
app.include_router(assets.router)
app.include_router(renders.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    return {"status": "ok"}
