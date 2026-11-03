import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.database import engine, Base, SessionLocal
from app.core.init_db import configure_gdal, init_db_schema
from app.core.logger import log_audit
from app.models.user import Rol, Usuario
from app.models.log import Log
from app.routers import auth, users, config, gis, system, empresas, proyectos, dibujo

# Configurar soporte para GDAL / Proj
configure_gdal()

# Inicializar extensiones, esquemas e índices de base de datos
init_db_schema(engine)

# Crear tablas del ORM
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Catastro API 2026",
    description="API de servicios catastrales y geográficos",
    version="1.0.0"
)

# Manejador global de excepciones no controladas
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    db = SessionLocal()
    try:
        log_audit(db, "ERROR", f"FALLA_INTERNA: {request.url.path}", str(exc))
    finally:
        db.close()
        
    return JSONResponse(
        status_code=500,
        content={"detail": "Ha ocurrido un error inesperado en el servidor. Los administradores han sido notificados."}
    )

# Configuración de orígenes permitidos (CORS)
frontend_url_env = os.getenv("FRONTEND_URL", "*")
default_allowed_origins = [
    "http://localhost:5173",
    "https://localhost:5173",
    "http://127.0.0.1:5173",
    "https://127.0.0.1:5173",
    "http://localhost:3000",
    "https://localhost:3000",
    "http://127.0.0.1:3000",
    "https://127.0.0.1:3000",
    "http://localhost:8000",
    "https://localhost:8000",
    "https://localhost",
    "http://localhost",
    "capacitor://localhost",
    "ionic://localhost"
]

origins = list(default_allowed_origins)
if frontend_url_env and frontend_url_env != "*":
    for u in frontend_url_env.split(","):
        trimmed = u.strip()
        if trimmed and trimmed not in origins:
            origins.append(trimmed)

origin_regex = r"(https?://.*|capacitor://.*|ionic://.*)"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de cabeceras HTTP de seguridad
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response

# Compresión GZIP para respuestas GeoJSON y JSON grandes
app.add_middleware(GZipMiddleware, minimum_size=1000)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Geoportal API is running"}

# Registro de routers de la API
app.include_router(config.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(empresas.router, prefix="/api")
app.include_router(proyectos.router, prefix="/api")
app.include_router(gis.router, prefix="/api")
app.include_router(system.router, prefix="/api")
app.include_router(dibujo.router, prefix="/api")

# Directorio estático de uploads
uploads_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(os.path.join(uploads_dir, "empresas"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
