import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

import db
import email_service
from backend.routes.application_routes import router as application_router
from backend.routes.auth_routes import router as auth_router
from backend.routes.drive_routes import router as drive_router
from backend.routes.upload_routes import router as upload_router


db.init_db()

app = FastAPI(
    title="Placement Portal & Dedicated Bulk Upload Engine",
    description="Integrated API for Authentication, Placement Drives, Student Profiles, and Bulk Ingestion/Export.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(drive_router)
app.include_router(upload_router)
app.include_router(application_router)

# Serve static frontend files
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")
if os.path.exists(PUBLIC_DIR):
    app.mount("/static", StaticFiles(directory=PUBLIC_DIR), name="static")


@app.get("/")
async def serve_index():
    index_path = os.path.join(PUBLIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Placement Tracking API is running."}


if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
