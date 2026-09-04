import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, RedirectResponse
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from bson import ObjectId

from config import settings
from utils.databaseUtil import init_db, close_db, db
from routes import (
    authRouter,
    emailVerificationRoutes,
    passwordResetRoutes,
    storeRouter,
    hostRouter,
    agentRouter
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("havento_python")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting HavenTo Python FastAPI server...")
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    await init_db()
    yield
    # Shutdown
    logger.info("🛑 Shutting down HavenTo Python server...")
    await close_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="HavenTo Python Backend — Matching Node.js Express Architecture",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"https://.*\.vercel\.app|http://localhost:.*|http://127\.0\.0\.1:.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Uploads Handler: Local files -> MongoDB GridFS 'photos' -> Fallback Unsplash image
FALLBACK_VILLA_IMAGE = "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=800&q=80"

@app.get("/uploads/{file_name:path}")
@app.get("/host/uploads/{file_name:path}")
@app.get("/homes/uploads/{file_name:path}")
async def get_upload_media(file_name: str):
    clean_name = os.path.basename(file_name)
    
    # 1. Local disk file
    local_path = os.path.join(settings.UPLOAD_DIR, clean_name)
    if os.path.exists(local_path) and os.path.isfile(local_path):
        return FileResponse(local_path)
        
    # 2. MongoDB Atlas GridFS bucket 'photos'
    try:
        if db.client:
            bucket = AsyncIOMotorGridFSBucket(db.client[settings.DATABASE_NAME], bucket_name="photos")
            potential_id = clean_name.split('.')[0]
            if ObjectId.is_valid(potential_id):
                oid = ObjectId(potential_id)
                grid_out = await bucket.open_download_stream(oid)
                async def file_iterator():
                    while True:
                        chunk = await grid_out.readchunk()
                        if not chunk:
                            break
                        yield chunk
                content_type = getattr(grid_out, "content_type", None) or "image/jpeg"
                return StreamingResponse(file_iterator(), media_type=content_type)
            else:
                grid_out = await bucket.open_download_stream_by_name(clean_name)
                async def file_iterator():
                    while True:
                        chunk = await grid_out.readchunk()
                        if not chunk:
                            break
                        yield chunk
                content_type = getattr(grid_out, "content_type", None) or "image/jpeg"
                return StreamingResponse(file_iterator(), media_type=content_type)
    except Exception as e:
        logger.debug(f"GridFS lookup for {file_name}: {e}")
        
    # 3. Always return a valid image so no property card is broken
    return RedirectResponse(FALLBACK_VILLA_IMAGE, status_code=307)

# Health Check Endpoints
@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "HavenTo Python FastAPI",
        "version": settings.VERSION,
        "database": "MongoDB Atlas"
    }

# Include Routers under /api
app.include_router(authRouter.router, prefix="/api")
app.include_router(authRouter.router, prefix="/api/auth")
app.include_router(emailVerificationRoutes.router, prefix="/api")
app.include_router(passwordResetRoutes.router, prefix="/api")
app.include_router(storeRouter.router, prefix="/api")
app.include_router(hostRouter.router, prefix="/api")
app.include_router(agentRouter.router, prefix="/api")

# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global error on {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "Internal Server Error", "error": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=settings.PORT, reload=True)
