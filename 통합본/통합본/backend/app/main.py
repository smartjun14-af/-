"""
실행: (backend 디렉토리에서) uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  
from .config import get_settings
from .database import Base, engine
from .exceptions import register_exception_handlers
from .routers import auth, dashboard, settings as settings_router, wallet

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="COIN Backend API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(wallet.router)
app.include_router(settings_router.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}
