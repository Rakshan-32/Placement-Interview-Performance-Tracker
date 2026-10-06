from datetime import datetime, timezone

from sqlalchemy import Boolean, Float, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def timestamp_value():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")


class User(Base):
    __tablename__ = "authenticate"

    uuid: Mapped[str] = mapped_column(String, primary_key=True)
    gmail: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=timestamp_value)
    department: Mapped[str] = mapped_column(String, default="CSE")


class Drive(Base):
    __tablename__ = "drives"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    job_role: Mapped[str] = mapped_column(String, nullable=False)
    ctc_lpa: Mapped[float] = mapped_column(Float, nullable=False)
    min_cgpa: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    allowed_branches: Mapped[str] = mapped_column(String, default="All", nullable=False)
    location: Mapped[str] = mapped_column(String, default="On Campus", nullable=False)
    status: Mapped[str] = mapped_column(String, default="Active", nullable=False)
    deadline: Mapped[str | None] = mapped_column(String)
    current_round: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=timestamp_value)
    company_type: Mapped[str] = mapped_column(String, default="PRODUCT")
    required_cgpa: Mapped[float] = mapped_column(Float, default=0.0)
    total_rounds: Mapped[int] = mapped_column(Integer, default=4)
    drive_date: Mapped[str | None] = mapped_column(String)


class StudentDriveResult(Base):
    __tablename__ = "student_drive_results"
    __table_args__ = (UniqueConstraint("drive_id", "gmail"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    drive_id: Mapped[str] = mapped_column(String, nullable=False)
    gmail: Mapped[str] = mapped_column(String, nullable=False)
    result: Mapped[str] = mapped_column(String, nullable=False)
    round: Mapped[int] = mapped_column(Integer, default=1)
    score: Mapped[float | None] = mapped_column(Float)
    max_score: Mapped[float | None] = mapped_column(Float)
    feedback: Mapped[str | None] = mapped_column(Text)
    weakness_area: Mapped[str | None] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    attempt_date: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String, default=timestamp_value, onupdate=timestamp_value)


class MentorNote(Base):
    __tablename__ = "mentor_notes"

    note_id: Mapped[str] = mapped_column(String, primary_key=True)
    mentor_id: Mapped[str] = mapped_column(String, nullable=False)
    student_id: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=timestamp_value)
    updated_at: Mapped[str] = mapped_column(String, default=timestamp_value, onupdate=timestamp_value)


class MentorStudent(Base):
    __tablename__ = "mentor_students"
    __table_args__ = (UniqueConstraint("mentor_id", "student_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True)
    mentor_id: Mapped[str] = mapped_column(String, nullable=False)
    student_id: Mapped[str] = mapped_column(String, nullable=False)
    assigned_at: Mapped[str] = mapped_column(String, default=timestamp_value)


class Intervention(Base):
    __tablename__ = "interventions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    student_id: Mapped[str] = mapped_column(String, nullable=False)
    student_gmail: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    failure_summary: Mapped[str] = mapped_column(Text, nullable=False)
    ai_analysis: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String, default="MEDIUM", nullable=False)
    status: Mapped[str] = mapped_column(String, default="OPEN", nullable=False)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=timestamp_value)
    updated_at: Mapped[str] = mapped_column(String, default=timestamp_value, onupdate=timestamp_value)


class InterventionAction(Base):
    __tablename__ = "intervention_actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    intervention_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    weakness_area: Mapped[str | None] = mapped_column(Text)
    resources: Mapped[str | None] = mapped_column(Text)
    assigned_to: Mapped[str | None] = mapped_column(String)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    due_date: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=timestamp_value)
    updated_at: Mapped[str] = mapped_column(String, default=timestamp_value, onupdate=timestamp_value)


class StudentRoster(Base):
    __tablename__ = "students_roster"

    student_id: Mapped[str] = mapped_column(String, primary_key=True)
    register_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    department: Mapped[str] = mapped_column(String, nullable=False)
    cgpa: Mapped[float] = mapped_column(Float, nullable=False)
    tenth_percentage: Mapped[float | None] = mapped_column(Float)
    twelfth_percentage: Mapped[float | None] = mapped_column(Float)
    skills: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String, default=timestamp_value)


class UploadLog(Base):
    __tablename__ = "upload_logs"

    log_id: Mapped[str] = mapped_column(String, primary_key=True)
    upload_type: Mapped[str] = mapped_column(String, nullable=False)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False)
    skipped_count: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[str] = mapped_column(String, default=timestamp_value)
