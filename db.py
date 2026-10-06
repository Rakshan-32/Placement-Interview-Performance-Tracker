import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

from sqlalchemy import create_engine, delete, func, inspect, select, text, update
from sqlalchemy.orm import sessionmaker

from orm_models import (
    Base,
    Drive,
    Intervention,
    InterventionAction,
    MentorNote,
    MentorStudent,
    StudentDriveResult,
    StudentRoster,
    UploadLog,
    User,
)

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DB_PATH.replace(os.sep, '/')}")
engine_options = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat(sep=" ", timespec="seconds")


def _as_dict(entity):
    if entity is None:
        return None
    return {column.key: getattr(entity, column.key) for column in inspect(entity).mapper.column_attrs}


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


def get_db_connection():
    """Legacy raw connection kept for database inspection in existing tests."""
    conn = engine.raw_connection()
    if DATABASE_URL.startswith("sqlite"):
        conn.driver_connection.row_factory = sqlite3.Row
    return conn


def _migrate_existing_sqlite_schema():
    if not DATABASE_URL.startswith("sqlite"):
        return

    additions = {
        "authenticate": {
            "is_active": "BOOLEAN DEFAULT 1",
            "created_at": "TEXT",
            "department": "TEXT DEFAULT 'CSE'",
        },
        "drives": {
            "min_cgpa": "REAL DEFAULT 0.0",
            "allowed_branches": "TEXT DEFAULT 'All'",
            "location": "TEXT DEFAULT 'On Campus'",
            "status": "TEXT DEFAULT 'Active'",
            "deadline": "TEXT",
            "current_round": "INTEGER DEFAULT 1",
            "created_at": "TEXT",
            "company_type": "TEXT DEFAULT 'PRODUCT'",
            "required_cgpa": "REAL DEFAULT 0.0",
            "total_rounds": "INTEGER DEFAULT 4",
            "drive_date": "TEXT",
        },
        "student_drive_results": {
            "round": "INTEGER DEFAULT 1",
            "score": "REAL",
            "max_score": "REAL",
            "feedback": "TEXT",
            "weakness_area": "TEXT",
            "rejection_reason": "TEXT",
            "attempt_date": "TEXT",
            "updated_at": "TEXT",
        },
    }
    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in additions.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name not in existing:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


def init_db():
    """Create the ORM schema and preserve compatibility with older SQLite files."""
    Base.metadata.create_all(engine)
    _migrate_existing_sqlite_schema()

    with session_scope() as session:
        demo_users = {
            "coordinator@gmail.com": ("coord123", "Coordinator"),
            "student@gmail.com": ("student123", "Student"),
            "mentor@gmail.com": ("mentor123", "Mentor"),
            "department@gmail.com": ("dept123", "Department"),
            "dept.cse@gmail.com": ("dept123", "Department"),
            "recruiter@gmail.com": ("recruiter123", "Recruiter"),
        }
        for gmail, (password, role) in demo_users.items():
            user = session.scalar(select(User).where(func.lower(User.gmail) == gmail))
            if user is None:
                session.add(User(uuid=str(uuid.uuid4()), gmail=gmail, password=password, role=role, department="CSE", created_at=_now()))

        session.execute(update(User).where(func.lower(User.role) == "admin").values(role="Coordinator"))
        session.execute(delete(User).where(func.lower(User.gmail) == "admin@gmail.com"))
        session.flush()

        mentor = session.scalar(select(User).where(func.lower(User.gmail) == "mentor@gmail.com"))
        students = session.scalars(select(User).where(func.lower(User.role) == "student")).all()
        if mentor:
            for student in students:
                assigned = session.scalar(select(MentorStudent).where(
                    MentorStudent.mentor_id == mentor.uuid,
                    MentorStudent.student_id == student.uuid,
                ))
                if assigned is None:
                    session.add(MentorStudent(id=str(uuid.uuid4()), mentor_id=mentor.uuid, student_id=student.uuid))

        if session.scalar(select(func.count()).select_from(Drive)) == 0:
            sample_drives = [
                ("Microsoft", "Software Engineer - SDE I", 18.5, 8.0, "CSE, IT, ECE, AIDS", "Bangalore / Remote", "Active", "2026-10-15"),
                ("Goldman Sachs", "Analyst - Technology Division", 22.0, 8.5, "CSE, ECE, EEE", "Hyderabad", "Active", "2026-10-20"),
                ("Amazon", "Applied Scientist / SDE", 28.0, 8.2, "CSE, IT, AIDS", "Chennai", "Upcoming", "2026-11-01"),
            ]
            for company, role, ctc, cgpa, branches, location, status, deadline in sample_drives:
                session.add(Drive(
                    id=str(uuid.uuid4()), company_name=company, job_role=role, ctc_lpa=ctc,
                    min_cgpa=cgpa, allowed_branches=branches, location=location,
                    status=status, deadline=deadline, current_round=1, created_at=_now(),
                ))


def get_user_by_gmail(gmail):
    with SessionLocal() as session:
        user = session.scalar(select(User).where(func.lower(User.gmail) == gmail.strip().lower()))
        return _as_dict(user)


def get_user_by_id(user_id):
    with SessionLocal() as session:
        return _as_dict(session.get(User, user_id))


def get_all_users():
    with SessionLocal() as session:
        users = session.scalars(select(User).order_by(User.gmail)).all()
        return [{"uuid": user.uuid, "gmail": user.gmail, "role": user.role} for user in users]


def get_all_drives():
    with SessionLocal() as session:
        return [_as_dict(drive) for drive in session.scalars(select(Drive).order_by(Drive.created_at.desc())).all()]


def get_drive(drive_id):
    with SessionLocal() as session:
        return _as_dict(session.get(Drive, drive_id))


def create_drive(company_name, job_role, ctc_lpa, min_cgpa, allowed_branches, location, status="Active", deadline=None):
    drive = Drive(
        id=str(uuid.uuid4()), company_name=company_name, job_role=job_role, ctc_lpa=ctc_lpa,
        min_cgpa=min_cgpa, allowed_branches=allowed_branches, location=location,
        status=status, deadline=deadline, current_round=1, created_at=_now(),
    )
    with session_scope() as session:
        session.add(drive)
        session.flush()
        return _as_dict(drive)


def _result_dict(result, drive=None):
    item = _as_dict(result)
    if drive:
        item.update({"company_name": drive.company_name, "job_role": drive.job_role, "ctc_lpa": drive.ctc_lpa, "location": drive.location})
    return item


def increment_student_drive_round(drive_id, gmail):
    email = gmail.strip().lower()
    with session_scope() as session:
        drive = session.get(Drive, drive_id)
        existing = session.scalar(select(StudentDriveResult).where(
            StudentDriveResult.drive_id == drive_id,
            func.lower(StudentDriveResult.gmail) == email,
        ))
        new_round = (existing.round + 1) if existing and existing.round is not None else max((drive.current_round if drive else 1), 1) + 1
        if existing:
            existing.round = new_round
            existing.result = f"Shortlisted for Round {new_round}"
            existing.updated_at = _now()
        else:
            session.add(StudentDriveResult(
                id=str(uuid.uuid4()), drive_id=drive_id, gmail=email,
                result=f"Shortlisted for Round {new_round}", round=new_round, updated_at=_now(),
            ))
        return {"gmail": email, "round": new_round, "result": f"Shortlisted for Round {new_round}"}


def increment_drive_current_round(drive_id):
    with session_scope() as session:
        drive = session.get(Drive, drive_id)
        if drive:
            drive.current_round = (drive.current_round or 1) + 1


def upsert_student_drive_result(drive_id, gmail, result, round_number=None, score=None, max_score=None,
                                feedback=None, weakness_area=None, rejection_reason=None, attempt_date=None):
    email = gmail.strip().lower()
    with session_scope() as session:
        record = session.scalar(select(StudentDriveResult).where(
            StudentDriveResult.drive_id == drive_id,
            func.lower(StudentDriveResult.gmail) == email,
        ))
        if record is None:
            record = StudentDriveResult(id=str(uuid.uuid4()), drive_id=drive_id, gmail=email, round=round_number or 1)
            session.add(record)
        record.result = result.strip()
        if round_number is not None:
            record.round = round_number
        record.score = score
        record.max_score = max_score
        record.feedback = feedback
        record.weakness_area = weakness_area
        record.rejection_reason = rejection_reason
        record.attempt_date = attempt_date
        record.updated_at = _now()


def get_drive_results(drive_id):
    with SessionLocal() as session:
        return [_result_dict(result) for result in session.scalars(
            select(StudentDriveResult).where(StudentDriveResult.drive_id == drive_id).order_by(StudentDriveResult.updated_at.desc())
        ).all()]


def get_student_drive_results(gmail):
    email = gmail.strip().lower()
    with SessionLocal() as session:
        rows = session.execute(
            select(StudentDriveResult, Drive)
            .join(Drive, StudentDriveResult.drive_id == Drive.id)
            .where(func.lower(StudentDriveResult.gmail) == email)
            .order_by(StudentDriveResult.updated_at.desc())
        ).all()
        return [_result_dict(result, drive) for result, drive in rows]


def get_students_for_scope(user_id, role, department=None):
    normalized = (role or "").strip().lower()
    with SessionLocal() as session:
        query = select(User).where(func.lower(User.role) == "student")
        if normalized == "student":
            query = query.where(User.uuid == user_id)
        elif normalized in {"department", "dept"}:
            query = query.where(func.upper(func.coalesce(User.department, "CSE")) == (department or "CSE").upper())
        elif normalized == "mentor":
            query = query.join(MentorStudent, MentorStudent.student_id == User.uuid).where(MentorStudent.mentor_id == user_id)
        elif normalized not in {"coordinator", "admin"}:
            query = query.where(False)
        return [{"uuid": user.uuid, "gmail": user.gmail, "role": user.role, "department": user.department} for user in session.scalars(query.order_by(func.lower(User.gmail))).all()]


def get_student_analysis_records(gmail):
    return get_student_drive_results(gmail)


def _intervention_dict(session, intervention):
    item = _as_dict(intervention)
    actions = session.scalars(select(InterventionAction).where(
        InterventionAction.intervention_id == intervention.id
    ).order_by(InterventionAction.created_at)).all()
    item["actions"] = [{**_as_dict(action), "completed": bool(action.completed)} for action in actions]
    user = session.scalar(select(User).where(func.lower(User.gmail) == intervention.student_gmail.lower()))
    item["department"] = user.department if user else None
    return item


def get_interventions(student_gmail=None, student_gmails=None):
    with SessionLocal() as session:
        query = select(Intervention).order_by(Intervention.updated_at.desc(), Intervention.created_at.desc())
        if student_gmail:
            query = query.where(func.lower(Intervention.student_gmail) == student_gmail.lower())
        elif student_gmails is not None:
            if not student_gmails:
                return []
            query = query.where(func.lower(Intervention.student_gmail).in_([email.lower() for email in student_gmails]))
        return [_intervention_dict(session, item) for item in session.scalars(query).all()]


def save_intervention(intervention, actions):
    intervention_id = intervention.get("id") or str(uuid.uuid4())
    with session_scope() as session:
        item = Intervention(
            id=intervention_id, student_id=intervention["student_id"],
            student_gmail=intervention["student_gmail"].lower(), title=intervention["title"],
            failure_summary=intervention["failure_summary"], ai_analysis=intervention["ai_analysis"],
            priority=intervention.get("priority", "MEDIUM"), status=intervention.get("status", "OPEN"),
            created_by=intervention["created_by"], created_at=_now(), updated_at=_now(),
        )
        session.add(item)
        for action in actions:
            session.add(InterventionAction(
                id=str(uuid.uuid4()), intervention_id=intervention_id, title=action["title"],
                weakness_area=action.get("weakness_area"), resources=action.get("resources"),
                assigned_to=action.get("assigned_to"), completed=bool(action.get("completed")),
                notes=action.get("notes"), due_date=action.get("due_date"), created_at=_now(), updated_at=_now(),
            ))
        session.flush()
        older = session.scalars(select(Intervention).where(
            func.lower(Intervention.student_gmail) == intervention["student_gmail"].lower(),
            Intervention.id != intervention_id,
        ).order_by(Intervention.updated_at.desc(), Intervention.created_at.desc())).all()
        for old in older[2:]:
            session.query(InterventionAction).filter(InterventionAction.intervention_id == old.id).delete()
            session.delete(old)
    return get_interventions(student_gmail=intervention["student_gmail"])[0]


def update_intervention_status(intervention_id, new_status):
    with session_scope() as session:
        item = session.get(Intervention, intervention_id)
        if not item:
            return False
        item.status = new_status
        item.updated_at = _now()
        return True


def update_intervention_action(action_id, completed=None, notes=None):
    if completed is None and notes is None:
        return False
    with session_scope() as session:
        action = session.get(InterventionAction, action_id)
        if not action:
            return False
        if completed is not None:
            action.completed = completed
        if notes is not None:
            action.notes = notes
        action.updated_at = _now()
        parent = session.get(Intervention, action.intervention_id)
        if parent:
            parent.updated_at = _now()
        return True


def get_student_profile_by_email(email):
    with SessionLocal() as session:
        student = session.scalar(select(StudentRoster).where(func.lower(StudentRoster.email) == email.strip().lower()))
        if not student:
            return None
        result = _as_dict(student)
        result["skills_list"] = [item.strip() for item in (student.skills or "").split(",") if item.strip()]
        return result


def get_drive_results_count(drive_id):
    with SessionLocal() as session:
        return session.scalar(select(func.count()).select_from(StudentDriveResult).where(StudentDriveResult.drive_id == drive_id)) or 0


def _normalize_role(role):
    return {
        "student": "Student", "mentor": "Mentor", "coordinator": "Coordinator", "admin": "Coordinator",
        "recruiter": "Recruiter", "department": "Department", "dept": "Department",
    }.get(role.strip().lower(), "Student")


def _default_password(role):
    return {"Student": "student123", "Mentor": "mentor123", "Coordinator": "coord123", "Department": "dept123", "Recruiter": "recruiter123"}.get(role, "user123")


def bulk_grant_user_access(users_list):
    created_count = updated_count = 0
    processed = []
    with session_scope() as session:
        for item in users_list:
            gmail = item.get("gmail", "").strip().lower()
            if not gmail or "@" not in gmail:
                continue
            role = _normalize_role(item.get("role", "Student"))
            password = item.get("password", "").strip() if item.get("password") else None
            user = session.scalar(select(User).where(func.lower(User.gmail) == gmail))
            if user:
                user.role = role
                if password:
                    user.password = password
                updated_count += 1
                processed.append({"uuid": user.uuid, "gmail": gmail, "role": role, "password": password or user.password, "action": "Updated Role & Password" if password else "Updated Role"})
            else:
                final_password = password or _default_password(role)
                user = User(uuid=str(uuid.uuid4()), gmail=gmail, password=final_password, role=role, department="CSE", created_at=_now())
                session.add(user)
                created_count += 1
                processed.append({"uuid": user.uuid, "gmail": gmail, "role": role, "password": final_password, "action": "Created Account"})
    return {"created_count": created_count, "updated_count": updated_count, "total_processed": len(processed), "processed_users": processed}


def grant_single_user_access(gmail, role="Student", password=None):
    gmail = gmail.strip().lower()
    role = _normalize_role(role)
    with session_scope() as session:
        user = session.scalar(select(User).where(func.lower(User.gmail) == gmail))
        if user:
            has_password = bool(password and password.strip())
            user.role = role
            if has_password:
                user.password = password.strip()
            return {"uuid": user.uuid, "gmail": gmail, "role": role, "password": user.password, "action": "Updated Role & Password" if has_password else "Updated Role"}
        final_password = password.strip() if password and password.strip() else _default_password(role)
        user = User(uuid=str(uuid.uuid4()), gmail=gmail, password=final_password, role=role, department="CSE", created_at=_now())
        session.add(user)
        return {"uuid": user.uuid, "gmail": gmail, "role": role, "password": final_password, "action": "Created Account"}


def get_mentor_notes(mentor_id, student_id):
    with SessionLocal() as session:
        return [_as_dict(note) for note in session.scalars(select(MentorNote).where(MentorNote.student_id == student_id).order_by(MentorNote.created_at.desc())).all()]


def create_mentor_note(mentor_id, student_id, content):
    note = MentorNote(note_id=str(uuid.uuid4()), mentor_id=mentor_id, student_id=student_id, content=content.strip(), created_at=_now(), updated_at=_now())
    with session_scope() as session:
        session.add(note)
        session.flush()
        return _as_dict(note)


def update_mentor_note(note_id, content):
    with session_scope() as session:
        note = session.get(MentorNote, note_id)
        if not note:
            return None
        note.content = content.strip()
        note.updated_at = _now()
        return _as_dict(note)


def delete_mentor_note(note_id):
    with session_scope() as session:
        note = session.get(MentorNote, note_id)
        if note:
            session.delete(note)
            return True
    return False


def _dashboard_students(session, dept_code, mentor_mode=False):
    users = session.scalars(select(User).where(func.lower(User.role) == "student").order_by(User.gmail)).all()
    mentors = ["Dr. Ramesh Kumar", "Prof. Anitha S", "Dr. Vijay P"]
    students = []
    placed = []
    at_risk = 0
    total_ctc = 0
    highest_ctc = 0
    for index, user in enumerate(users):
        rows = session.execute(select(StudentDriveResult, Drive).join(Drive, StudentDriveResult.drive_id == Drive.id, isouter=True).where(func.lower(StudentDriveResult.gmail) == user.gmail.lower()).order_by(StudentDriveResult.updated_at.desc())).all()
        results = [_result_dict(result, drive) for result, drive in rows]
        status = "Active"
        placed_info = None
        for result in results:
            value = (result.get("result") or "").lower()
            if any(word in value for word in ("selected", "placed", "hired")):
                status, placed_info = "Placed", result
                break
            if "rejected" in value or "failed" in value:
                status = "At Risk"
        if status == "At Risk":
            at_risk += 1
        student = {
            "student_id": user.uuid, "name": user.gmail.split("@")[0].replace(".", " ").replace("_", " ").title(),
            "register_number": f"312321{104000 + index + 1:06d}", "department": dept_code,
            "cgpa": round((7.5 if mentor_mode else 7.4) + (index % 20) * 0.1, 1),
            "tenth": round(80 + (index % 15), 1), "twelfth": round(82 + (index % 15), 1),
            "placement_marks": 60 + (index % 35), "status": status, "email": user.gmail,
            "phone": f"9876543{index:03d}", "assigned_mentor": mentors[index % len(mentors)],
        }
        if status == "Placed" and placed_info:
            student.update(company=placed_info.get("company_name", "Tech Corp"), job_role=placed_info.get("job_role", "Software Engineer"), ctc=placed_info.get("ctc_lpa", 12.0))
            placed.append(student)
            total_ctc += student["ctc"]
            highest_ctc = max(highest_ctc, student["ctc"])
        students.append(student)
    return students, placed, at_risk, total_ctc, highest_ctc


def get_mentor_dashboard_data(mentor_gmail="mentor@gmail.com"):
    with SessionLocal() as session:
        mentees, placed, at_risk, _, _ = _dashboard_students(session, "CSE", mentor_mode=True)
    return {"mentees": mentees, "placed_mentees": placed, "interventions": [], "metrics": {"total_mentees": len(mentees), "placed_count": len(placed), "placement_rate": round(len(placed) / len(mentees) * 100, 1) if mentees else 0.0, "active_interventions": 0, "at_risk_count": at_risk}}


def get_department_dashboard_data(dept_code="CSE"):
    with SessionLocal() as session:
        students, placed, at_risk, total_ctc, highest_ctc = _dashboard_students(session, dept_code)
    mentors = [{"id": f"mentor-{index}", "name": name, "email": f"{name.lower().replace(' ', '.')}@stjosephs.ac.in", "department": dept_code, "specialization": specialization, "assigned_mentees": count, "placed_mentees": placed_count, "active_interventions": active} for index, (name, specialization, count, placed_count, active) in enumerate([("Dr. Ramesh Kumar", "Data Structures & Algorithms", 18, 14, 2), ("Prof. Anitha S", "System Design & Web Tech", 15, 12, 1), ("Dr. Vijay P", "Aptitude & Machine Learning", 12, 8, 3)], 1)]
    return {"department": {"code": dept_code, "name": "Computer Science & Engineering" if dept_code == "CSE" else f"Department of {dept_code}"}, "mentors": mentors, "students": students, "placed_students": placed, "interventions": [], "metrics": {"total_students": len(students), "placed_count": len(placed), "placement_rate": round(len(placed) / len(students) * 100, 1) if students else 0.0, "at_risk_count": at_risk, "total_mentors": len(mentors), "avg_ctc": round(total_ctc / len(placed), 2) if placed else 9.5, "highest_ctc": highest_ctc or 22.0}}


def upsert_company_drive_record(company_name, job_role, ctc_lpa, company_type="PRODUCT", required_cgpa=0.0, allowed_branches="All", location="On Campus", total_rounds=4, drive_date=None, status="Active", drive_id=None):
    company_name, job_role = company_name.strip(), job_role.strip()
    with session_scope() as session:
        drive = session.get(Drive, drive_id) if drive_id else session.scalar(select(Drive).where(func.lower(Drive.company_name) == company_name.lower(), func.lower(Drive.job_role) == job_role.lower()))
        action = "Updated" if drive else "Created"
        if not drive:
            slug = "".join(character for character in f"{company_name.lower().replace(' ', '-')}-{job_role.lower().replace(' ', '-')}-2026" if character.isalnum() or character == "-")
            drive = Drive(id=slug if len(slug) <= 40 else str(uuid.uuid4()), created_at=_now(), current_round=1)
            session.add(drive)
        drive.company_name, drive.job_role, drive.ctc_lpa = company_name, job_role, ctc_lpa
        drive.company_type, drive.required_cgpa = company_type, required_cgpa
        drive.allowed_branches, drive.location, drive.total_rounds = allowed_branches, location, total_rounds
        drive.drive_date, drive.status = drive_date, status
        return {"id": drive.id, "company_name": company_name, "job_role": job_role, "ctc_lpa": ctc_lpa, "company_type": company_type, "required_cgpa": required_cgpa, "allowed_branches": allowed_branches, "total_rounds": total_rounds, "location": location, "drive_date": drive_date, "status": status, "action": action}


def process_shortlist_record(drive_id, email, base_round=None):
    email = email.strip().lower()
    with session_scope() as session:
        existing = session.scalar(select(StudentDriveResult).where(StudentDriveResult.drive_id == drive_id, func.lower(StudentDriveResult.gmail) == email))
        new_round = existing.round + 1 if existing and existing.round is not None else (base_round or 1) + 1
        result = f"Shortlisted for Round {new_round}"
        if existing:
            existing.round, existing.result, existing.updated_at = new_round, result, _now()
        else:
            session.add(StudentDriveResult(id=str(uuid.uuid4()), drive_id=drive_id, gmail=email, result=result, round=new_round, updated_at=_now()))
        return {"gmail": email, "round": new_round, "result": result, "status": "Promoted"}


def process_verdict_record(drive_id, email, verdict, round_num=None, score=None, max_score=None, feedback=None, weakness_area=None, rejection_reason=None, attempt_date=None):
    upsert_student_drive_result(drive_id, email, verdict, round_num, score, max_score, feedback, weakness_area, rejection_reason, attempt_date)
    return {"gmail": email.strip().lower(), "result": verdict.strip(), "round": round_num or 1, "score": score, "status": "Updated"}


def upsert_user_account(email, role="Student", password=None):
    result = grant_single_user_access(email, role, password)
    return {"uuid": result["uuid"], "gmail": result["gmail"], "role": result["role"], "action": result["action"]}


def upsert_student_roster_record(register_number, name, email, department, cgpa, tenth=None, twelfth=None, skills=""):
    email, register_number = email.strip().lower(), register_number.strip().upper()
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
        return [_as_dict(student) for student in session.scalars(select(StudentRoster).order_by(StudentRoster.created_at.desc())).all()]


def record_upload_log(upload_type, filename, total_rows, processed_count, skipped_count, status="SUCCESS"):
    log = UploadLog(log_id=str(uuid.uuid4()), upload_type=upload_type, filename=filename, total_rows=total_rows, processed_count=processed_count, skipped_count=skipped_count, status=status, created_at=_now())
    with session_scope() as session:
        session.add(log)
    return log.log_id


def get_upload_logs():
    with SessionLocal() as session:
        return [_as_dict(log) for log in session.scalars(select(UploadLog).order_by(UploadLog.created_at.desc())).all()]


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
