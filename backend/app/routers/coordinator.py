from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Coordinator

router = APIRouter(prefix="/api/coordinator", tags=["coordinator"])


class CoordinatorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    coordinator_id: str
    name: str
    email: str
    department: str | None = None


@router.get("/", response_model=list[CoordinatorOut])
def list_coordinators(db: Session = Depends(get_db)):
    return db.query(Coordinator).order_by(Coordinator.name).all()
