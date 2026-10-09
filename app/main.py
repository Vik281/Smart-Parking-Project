from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.database.seed import seed_if_empty
from app.database.session import Base, SessionLocal, engine
from app.services.errors import ServiceError

frontend_folder = Path(__file__).parent.parent / "frontend"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Runs once at startup: create tables that don't exist yet, then add demo data.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_if_empty(db)
    yield


app = FastAPI(title="ParkShare API", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=frontend_folder), name="static")


@app.exception_handler(ServiceError)
def handle_service_error(_request: Request, error: ServiceError):
    # One place that translates business errors into HTTP responses.
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(frontend_folder / "index.html")
