from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
import app.models  # noqa: F401 — registers all models with Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Placement Intervention API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers.intervention import router as intervention_router
from app.routers.access import router as access_router
from app.routers.student import router as student_router
from app.routers.mentor import router as mentor_router
from app.routers.department import router as department_router
from app.routers.coordinator import router as coordinator_router

app.include_router(intervention_router)
app.include_router(access_router)
app.include_router(student_router)
app.include_router(mentor_router)
app.include_router(department_router)
app.include_router(coordinator_router)


@app.get("/health")
def health():
    return {"status": "ok"}
