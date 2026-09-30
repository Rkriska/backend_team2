from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api.v1.router import router as v1_router
from app.api.v1.endpoints.health import router as health_router
@asynccontextmanager
async def lifespan(app):
 Path(settings.UPLOAD_DIR).mkdir(parents=True,exist_ok=True)
 yield
app=FastAPI(title='AITF Procurement Screening API',version='1.0.0',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=['*'] if settings.CORS_ORIGINS=='*' else settings.CORS_ORIGINS.split(','),allow_credentials=False,allow_methods=['*'],allow_headers=['*'])
app.include_router(health_router);app.include_router(v1_router)
