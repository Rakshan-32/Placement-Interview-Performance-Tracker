import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

from orm_models import Base, Drive, StudentDriveResult, StudentRoster, UploadLog, User
from .config import DB_PATH

DATABASE_URL = os.environ.get("BULK_DATABASE_URL", f"sqlite:///{DB_PATH.replace(os.sep, '/')}")
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")


def _as_dict(entity):
    return {column.key: getattr(entity, column.key) for column in entity.__mapper__.column_attrs}


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_connection():
    """Legacy raw connection retained only for the standalone test reset fixture."""
    conn = engine.raw_connection()
    if DATABASE_URL.startswith("sqlite"):
        conn.driver_connection.row_factory = sqlite3.Row
    return conn


def init_db():
    Base.metadata.create_all(engine)
    with session_scope() as session:
        if session.scalar(select(func.count()).select_from(Drive)) == 0:
            for drive_id, company, role, ctc, round_number in [
                ("tcs-drive-2026", "TCS Digital", "Software Engineer", 7.5, 1),
                ("zoho-drive-2026", "Zoho Corporation", "Member Technical Staff", 8.4, 1),
                ("infosys-drive-2026", "Infosys", "Systems Engineer Specialist", 6.0, 1),
            ]:
                session.add(Drive(id=drive_id, company_name=company, job_role=role, ctc_lpa=ctc, current_round=round_number, created_at=_now()))


def _result_dict(result):
    return _as_dict(result)


def get_drive(drive_id):
    with SessionLocal() as session:
        drive = session.get(Drive, drive_id)
        return _as_dict(drive) if drive else None


def get_all_drives():
    with SessionLocal() as session:
        return [_as_dict(drive) for drive in session.scalars(select(Drive).order_by(Drive.created_at.desc())).all()]


def upsert_company_drive_record(company_name, job_role, ctc_lpa, company_type="PRODUCT", required_cgpa=0.0, allowed_branches="All", location="On Campus", total_rounds=4, drive_date=None, status="Active", drive_id=None):
    company_name, job_role = company_name.strip(), job_role.strip()
    with session_scope() as session:
        drive = session.get(Drive, drive_id) if drive_id else session.scalar(select(Drive).where(func.lower(Drive.company_name) == company_name.lower(), func.lower(Drive.job_role) == job_role.lower()))
        action = "Updated" if drive else "Created"
        if not drive:
            slug = "".join(char for char in f"{company_name.lower().replace(' ', '-')}-{job_role.lower().replace(' ', '-')}-2026" if char.isalnum() or char == "-")
            drive = Drive(id=slug if len(slug) <= 40 else str(uuid.uuid4()), created_at=_now(), current_round=1)
            session.add(drive)
        drive.company_name, drive.job_role, drive.ctc_lpa = company_name, job_role, ctc_lpa
        drive.company_type, drive.required_cgpa = company_type, required_cgpa
        drive.allowed_branches, drive.location, drive.total_rounds = allowed_branches, location, total_rounds
        drive.drive_date, drive.status = drive_date, status
        return {"id": drive.id, "company_name": company_name, "job_role": job_role, "ctc_lpa": ctc_lpa, "company_type": company_type, "required_cgpa": required_cgpa, "allowed_branches": allowed_branches, "location": location, "total_rounds": total_rounds, "drive_date": drive_date, "status": status, "action": action}


def process_shortlist_record(drive_id, email, base_round=None):
    email = email.strip().lower()
    with session_scope() as session:
        record = session.scalar(select(StudentDriveResult).where(StudentDriveResult.drive_id == drive_id, func.lower(StudentDriveResult.gmail) == email))
        new_round = record.round + 1 if record and record.round is not None else (base_round or 1) + 1
        result = f"Shortlisted for Round {new_round}"
        if record:
            record.round, record.result, record.updated_at = new_round, result, _now()
        else:
            session.add(StudentDriveResult(id=str(uuid.uuid4()), drive_id=drive_id, gmail=email, result=result, round=new_round, updated_at=_now()))
        return {"gmail": email, "round": new_round, "result": result, "status": "Promoted"}


def process_verdict_record(drive_id, email, verdict, round_num=None, score=None, max_score=None, feedback=None, weakness_area=None, rejection_reason=None, attempt_date=None):
    email = email.strip().lower()
    with session_scope() as session:
        record = session.scalar(select(StudentDriveResult).where(StudentDriveResult.drive_id == drive_id, func.lower(StudentDriveResult.gmail) == email))
        if not record:
            record = StudentDriveResult(id=str(uuid.uuid4()), drive_id=drive_id, gmail=email, round=round_num or 1)
            session.add(record)
        record.result, record.round = verdict.strip(), round_num or record.round or 1
        record.score, record.max_score = score, max_score
        record.feedback, record.weakness_area = feedback, weakness_area
        record.rejection_reason, record.attempt_date, record.updated_at = rejection_reason, attempt_date, _now()
        return {"gmail": email, "result": verdict.strip(), "round": record.round, "score": score, "status": "Updated"}


def get_drive_results(drive_id):
    with SessionLocal() as session:
        return [_result_dict(item) for item in session.scalars(select(StudentDriveResult).where(StudentDriveResult.drive_id == drive_id).order_by(StudentDriveResult.updated_at.desc())).all()]


def upsert_user_account(email, role="Student", password=None):
    role_map = {"student": "Student", "mentor": "Mentor", "coordinator": "Coordinator", "admin": "Coordinator", "recruiter": "Recruiter", "department": "Department", "dept": "Department"}
    role = role_map.get(role.strip().lower(), "Student")
    email = email.strip().lower()
    defaults = {"Student": "student123", "Mentor": "mentor123", "Coordinator": "coord123", "Department": "dept123", "Recruiter": "recruiter123"}
    with session_scope() as session:
        user = session.scalar(select(User).where(func.lower(User.gmail) == email))
        action = "Updated" if user else "Created"
        if not user:
            user = User(uuid=str(uuid.uuid4()), gmail=email, password=password or defaults.get(role, "user123"), role=role, department="CSE", created_at=_now())
            session.add(user)
        else:
            user.role = role
            if password:
                user.password = password
        return {"uuid": user.uuid, "gmail": email, "role": role, "action": action}


def upsert_student_roster_record(register_number, name, email, department, cgpa, tenth=None, twelfth=None, skills=""):
    register_number, email = register_number.strip().upper(), email.strip().lower()
    with session_scope() as session:
        student = session.scalar(select(StudentRoster).where(StudentRoster.register_number == register_number))
        if not student:
            student = StudentRoster(student_id=str(uuid.uuid4()), register_number=register_number)
            session.add(student)
        student.name, student.email, student.department = name.strip(), email, department.strip().upper()
        student.cgpa, student.tenth_percentage, student.twelfth_percentage, student.skills = cgpa, tenth, twelfth, skills.strip()
        return {"register_number": register_number, "name": student.name, "email": email, "department": student.department, "cgpa": cgpa}


def get_all_student_roster():
    with SessionLocal() as session:
        return [_as_dict(item) for item in session.scalars(select(StudentRoster).order_by(StudentRoster.created_at.desc())).all()]


def get_all_users():
    with SessionLocal() as session:
        return [{"uuid": item.uuid, "gmail": item.gmail, "role": item.role} for item in session.scalars(select(User).order_by(User.gmail)).all()]


def record_upload_log(upload_type, filename, total_rows, processed_count, skipped_count, status="SUCCESS"):
    log = UploadLog(log_id=str(uuid.uuid4()), upload_type=upload_type, filename=filename, total_rows=total_rows, processed_count=processed_count, skipped_count=skipped_count, status=status, created_at=_now())
    with session_scope() as session:
        session.add(log)
    return log.log_id


def get_upload_logs():
    with SessionLocal() as session:
        return [_as_dict(item) for item in session.scalars(select(UploadLog).order_by(UploadLog.created_at.desc())).all()]
