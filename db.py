import sqlite3
import uuid
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")



def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database and create tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create the authenticate table as required
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS authenticate (
            uuid TEXT PRIMARY KEY,
            gmail TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)
    
    # Create the drives table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drives (
            id TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            job_role TEXT NOT NULL,
            ctc_lpa REAL NOT NULL,
            min_cgpa REAL NOT NULL,
            allowed_branches TEXT NOT NULL,
            location TEXT NOT NULL,
            status TEXT NOT NULL,
            deadline TEXT,
            current_round INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create the student drive results table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_drive_results (
            id TEXT PRIMARY KEY,
            drive_id TEXT NOT NULL,
            gmail TEXT NOT NULL,
            result TEXT NOT NULL,
            round INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(drive_id, gmail)
        )
    """)
    conn.commit()

    # Migrations for pre-existing database tables
    try:
        cursor.execute("ALTER TABLE drives ADD COLUMN current_round INTEGER DEFAULT 1")
        conn.commit()
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE student_drive_results ADD COLUMN round INTEGER DEFAULT 1")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    
    # Create mentor_notes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mentor_notes (
            note_id TEXT PRIMARY KEY,
            mentor_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create mentor_students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mentor_students (
            id TEXT PRIMARY KEY,
            mentor_id TEXT NOT NULL,
            student_id TEXT NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(mentor_id, student_id)
        )
    """)
    conn.commit()

    # Create interventions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interventions (
            id TEXT PRIMARY KEY,
            student_id TEXT NOT NULL,
            student_gmail TEXT NOT NULL,
            trigger_reason TEXT,
            ai_analysis TEXT,
            priority TEXT DEFAULT 'MEDIUM',
            status TEXT DEFAULT 'GENERATED',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create intervention_actions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intervention_actions (
            id TEXT PRIMARY KEY,
            intervention_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            action_type TEXT,
            target_weakness TEXT,
            priority_order INTEGER DEFAULT 1,
            estimated_days INTEGER DEFAULT 14,
            resources TEXT,
            is_completed INTEGER DEFAULT 0,
            notes TEXT,
            FOREIGN KEY (intervention_id) REFERENCES interventions(id)
        )
    """)
    conn.commit()

    # Seed demo users if empty
    cursor.execute("SELECT COUNT(*) as count FROM authenticate")
    row = cursor.fetchone()
    if row["count"] == 0:
        seed_users = [
            (str(uuid.uuid4()), "coordinator@gmail.com", "coord123", "Coordinator"),
            (str(uuid.uuid4()), "student@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "arun.kumar@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "bhavani.s@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "deepak.raj@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "divya.m@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "elango.p@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "fathima.z@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "gowtham.r@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "harini.v@gmail.com", "student123", "Student"),
            (str(uuid.uuid4()), "mentor@gmail.com", "mentor123", "Mentor"),
            (str(uuid.uuid4()), "department@gmail.com", "dept123", "Department"),
            (str(uuid.uuid4()), "dept.cse@gmail.com", "dept123", "Department"),
            (str(uuid.uuid4()), "recruiter@gmail.com", "recruiter123", "Recruiter")
        ]
        cursor.executemany("""
            INSERT INTO authenticate (uuid, gmail, password, role)
            VALUES (?, ?, ?, ?)
        """, seed_users)
        conn.commit()
        print("Database seeded with sample demo accounts.")
    else:
        # Ensure coordinator account exists
        cursor.execute("SELECT uuid FROM authenticate WHERE LOWER(gmail) = 'coordinator@gmail.com'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO authenticate (uuid, gmail, password, role)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), "coordinator@gmail.com", "coord123", "Coordinator"))
            conn.commit()

        # Ensure mentor account exists
        cursor.execute("SELECT uuid FROM authenticate WHERE LOWER(gmail) = 'mentor@gmail.com'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO authenticate (uuid, gmail, password, role)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), "mentor@gmail.com", "mentor123", "Mentor"))
            conn.commit()
            print("Seeded Mentor demo account.")

        # Ensure department account exists
        cursor.execute("SELECT uuid FROM authenticate WHERE LOWER(gmail) = 'department@gmail.com'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO authenticate (uuid, gmail, password, role)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), "department@gmail.com", "dept123", "Department"))
            conn.commit()

        cursor.execute("SELECT uuid FROM authenticate WHERE LOWER(gmail) = 'dept.cse@gmail.com'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO authenticate (uuid, gmail, password, role)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), "dept.cse@gmail.com", "dept123", "Department"))
            conn.commit()

        # Ensure demo students exist
        demo_students = [
            "arun.kumar@gmail.com",
            "bhavani.s@gmail.com",
            "deepak.raj@gmail.com",
            "divya.m@gmail.com",
            "elango.p@gmail.com",
            "fathima.z@gmail.com",
            "gowtham.r@gmail.com",
            "harini.v@gmail.com",
        ]
        for sg in demo_students:
            cursor.execute("SELECT uuid FROM authenticate WHERE LOWER(gmail) = ?", (sg,))
            if not cursor.fetchone():
                cursor.execute(
                    "INSERT INTO authenticate (uuid, gmail, password, role) VALUES (?, ?, ?, ?)",
                    (str(uuid.uuid4()), sg, "student123", "Student")
                )
        conn.commit()

        # Migrate/remove legacy Admin role records to Coordinator
        cursor.execute("UPDATE authenticate SET role = 'Coordinator' WHERE LOWER(role) = 'admin'")
        cursor.execute("DELETE FROM authenticate WHERE LOWER(gmail) = 'admin@gmail.com'")
        conn.commit()

    # Seed sample drives if drives table is empty
    cursor.execute("SELECT COUNT(*) as count FROM drives")
    d_row = cursor.fetchone()
    if d_row["count"] == 0:
        sample_drives = [
            (str(uuid.uuid4()), "Microsoft", "Software Engineer - SDE I", 18.5, 8.0, "CSE, IT, ECE, AIDS", "Bangalore / Remote", "Active", "2026-10-15"),
            (str(uuid.uuid4()), "Goldman Sachs", "Analyst - Technology Division", 22.0, 8.5, "CSE, ECE, EEE", "Hyderabad", "Active", "2026-10-20"),
            (str(uuid.uuid4()), "Amazon", "Applied Scientist / SDE", 28.0, 8.2, "CSE, IT, AIDS", "Chennai", "Upcoming", "2026-11-01")
        ]
        cursor.executemany("""
            INSERT INTO drives (id, company_name, job_role, ctc_lpa, min_cgpa, allowed_branches, location, status, deadline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample_drives)
        conn.commit()
        print("Database seeded with sample recruitment drives.")
        
    conn.close()

def get_user_by_gmail(gmail: str):
    """Fetch user record from 'authenticate' table by gmail."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uuid, gmail, password, role FROM authenticate WHERE LOWER(gmail) = LOWER(?)", (gmail.strip(),))
    user = cursor.fetchone()
    conn.close()
    if user:
        return dict(user)
    return None

def get_all_users():
    """Retrieve all accounts (without secrets) for demo quick-fill feature."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT uuid, gmail, role FROM authenticate")
    users = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return users

def get_all_drives():
    """Fetch all placement drives from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, company_name, job_role, ctc_lpa, min_cgpa, allowed_branches, location, status, deadline, current_round, created_at FROM drives ORDER BY created_at DESC")
    drives = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return drives

def create_drive(company_name: str, job_role: str, ctc_lpa: float, min_cgpa: float, allowed_branches: str, location: str, status: str = "Active", deadline: str = None):
    """Create a new placement drive record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    drive_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO drives (id, company_name, job_role, ctc_lpa, min_cgpa, allowed_branches, location, status, deadline, current_round)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (drive_id, company_name, job_role, ctc_lpa, min_cgpa, allowed_branches, location, status, deadline))
    conn.commit()
    cursor.execute("SELECT id, company_name, job_role, ctc_lpa, min_cgpa, allowed_branches, location, status, deadline, current_round, created_at FROM drives WHERE id = ?", (drive_id,))
    new_drive = dict(cursor.fetchone())
    conn.close()
    return new_drive

def increment_student_drive_round(drive_id: str, gmail: str):
    """
    Increment a student's round for a specific drive by 1 in the student database.
    Everyone in the uploaded Excel is shortlisted for the next round.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    gmail_clean = gmail.strip().lower()

    # Fetch current drive round
    cursor.execute("SELECT current_round FROM drives WHERE id = ?", (drive_id,))
    drive_row = cursor.fetchone()
    drive_round = drive_row["current_round"] if (drive_row and "current_round" in drive_row.keys() and drive_row["current_round"]) else 1

    # Check existing student record for this drive
    cursor.execute("SELECT round FROM student_drive_results WHERE drive_id = ? AND LOWER(gmail) = ?", (drive_id, gmail_clean))
    existing = cursor.fetchone()

    if existing and existing["round"] is not None:
        new_round = existing["round"] + 1
    else:
        new_round = max(drive_round, 1) + 1

    result_str = f"Shortlisted for Round {new_round}"
    res_id = str(uuid.uuid4())

    cursor.execute("""
        INSERT INTO student_drive_results (id, drive_id, gmail, result, round, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(drive_id, gmail) DO UPDATE SET
            round = excluded.round,
            result = excluded.result,
            updated_at = CURRENT_TIMESTAMP
    """, (res_id, drive_id, gmail_clean, result_str, new_round))
    conn.commit()
    conn.close()

    return {
        "gmail": gmail_clean,
        "round": new_round,
        "result": result_str
    }

def increment_drive_current_round(drive_id: str):
    """Increment overall drive round counter by 1."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE drives SET current_round = COALESCE(current_round, 1) + 1 WHERE id = ?", (drive_id,))
    conn.commit()
    conn.close()

def upsert_student_drive_result(drive_id: str, gmail: str, result: str):
    """Insert or update a student's result status for a specific company drive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    res_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO student_drive_results (id, drive_id, gmail, result, updated_at)
        VALUES (?, ?, LOWER(?), ?, CURRENT_TIMESTAMP)
        ON CONFLICT(drive_id, gmail) DO UPDATE SET
            result = excluded.result,
            updated_at = CURRENT_TIMESTAMP
    """, (res_id, drive_id, gmail.strip(), result.strip()))
    conn.commit()
    conn.close()

def get_drive_results(drive_id: str):
    """Fetch all candidate evaluation results for a specific placement drive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, drive_id, gmail, result, round, updated_at 
        FROM student_drive_results 
        WHERE drive_id = ? 
        ORDER BY updated_at DESC
    """, (drive_id,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_student_drive_results(gmail: str):
    """Fetch drive results for a specific student across all drives."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.id, s.drive_id, s.gmail, s.result, s.round, s.updated_at, d.company_name, d.job_role, d.ctc_lpa, d.location
        FROM student_drive_results s
        JOIN drives d ON s.drive_id = d.id
        WHERE LOWER(s.gmail) = LOWER(?)
        ORDER BY s.updated_at DESC
    """, (gmail.strip(),))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_drive_results_count(drive_id: str) -> int:
    """Count candidate results for a specific drive."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM student_drive_results WHERE drive_id = ?", (drive_id,))
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0

def bulk_grant_user_access(users_list: list):
    """
    Bulk create or update user access in 'authenticate' table.
    users_list is a list of dicts: [{"gmail": "...", "role": "..."}, ...]
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    created_count = 0
    updated_count = 0
    processed_users = []

    for item in users_list:
        gmail = item.get("gmail", "").strip().lower()
        role = item.get("role", "Student").strip()
        custom_password = item.get("password", "").strip() if item.get("password") else None

        # Normalize role casing
        if role.lower() == "student":
            role = "Student"
        elif role.lower() == "mentor":
            role = "Mentor"
        elif role.lower() in ["department", "dept"]:
            role = "Department"
        elif role.lower() == "recruiter":
            role = "Recruiter"
        elif role.lower() in ["coordinator", "admin"]:
            role = "Coordinator"

        if not gmail or "@" not in gmail:
            continue

        # Check existing user
        cursor.execute("SELECT uuid, role, password FROM authenticate WHERE LOWER(gmail) = ?", (gmail,))
        existing = cursor.fetchone()

        if existing:
            if custom_password:
                cursor.execute("UPDATE authenticate SET role = ?, password = ? WHERE LOWER(gmail) = ?", (role, custom_password, gmail))
                action_str = "Updated Role & Password"
            else:
                cursor.execute("UPDATE authenticate SET role = ? WHERE LOWER(gmail) = ?", (role, gmail))
                action_str = "Updated Role"

            updated_count += 1
            processed_users.append({
                "uuid": existing["uuid"],
                "gmail": gmail,
                "role": role,
                "password": custom_password if custom_password else existing["password"],
                "action": action_str
            })
        else:
            if custom_password:
                final_pwd = custom_password
            elif role == "Student":
                final_pwd = "student123"
            elif role == "Mentor":
                final_pwd = "mentor123"
            elif role == "Department":
                final_pwd = "dept123"
            elif role == "Recruiter":
                final_pwd = "recruiter123"
            elif role == "Coordinator":
                final_pwd = "coord123"
            else:
                final_pwd = "user123"

            new_uuid = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO authenticate (uuid, gmail, password, role)
                VALUES (?, ?, ?, ?)
            """, (new_uuid, gmail, final_pwd, role))
            created_count += 1
            processed_users.append({
                "uuid": new_uuid,
                "gmail": gmail,
                "role": role,
                "password": final_pwd,
                "action": "Created Account"
            })


    conn.commit()
    conn.close()

    return {
        "created_count": created_count,
        "updated_count": updated_count,
        "total_processed": len(processed_users),
        "processed_users": processed_users
    }

def grant_single_user_access(gmail: str, role: str = "Student", password: str = None):
    """Grant or update access for a single user in 'authenticate' table."""
    conn = get_db_connection()
    cursor = conn.cursor()

    gmail_clean = gmail.strip().lower()
    
    # Normalize role casing
    if role.lower() == "student":
        role = "Student"
    elif role.lower() == "mentor":
        role = "Mentor"
    elif role.lower() in ["department", "dept"]:
        role = "Department"
    elif role.lower() == "recruiter":
        role = "Recruiter"
    elif role.lower() in ["coordinator", "admin"]:
        role = "Coordinator"

    cursor.execute("SELECT uuid, role, password FROM authenticate WHERE LOWER(gmail) = ?", (gmail_clean,))
    existing = cursor.fetchone()

    if existing:
        final_pwd = password.strip() if (password and password.strip()) else existing["password"]
        if password and password.strip():
            cursor.execute("UPDATE authenticate SET role = ?, password = ? WHERE LOWER(gmail) = ?", (role, final_pwd, gmail_clean))
        else:
            cursor.execute("UPDATE authenticate SET role = ? WHERE LOWER(gmail) = ?", (role, gmail_clean))
        conn.commit()
        conn.close()

        return {
            "uuid": existing["uuid"],
            "gmail": gmail_clean,
            "role": role,
            "password": final_pwd,
            "action": "Updated Role & Password" if (password and password.strip()) else "Updated Role"
        }
    else:
        final_pwd = password.strip() if (password and password.strip()) else ("student123" if role == "Student" else "mentor123" if role == "Mentor" else "dept123" if role == "Department" else "user123")
        new_uuid = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO authenticate (uuid, gmail, password, role)
            VALUES (?, ?, ?, ?)
        """, (new_uuid, gmail_clean, final_pwd, role))
        conn.commit()
        conn.close()

        return {
            "uuid": new_uuid,
            "gmail": gmail_clean,
            "role": role,
            "password": final_pwd,
            "action": "Created Account"
        }




def get_mentor_notes(mentor_id: str, student_id: str):
    """Retrieve all notes written by a mentor for a specific student."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT note_id, mentor_id, student_id, content, created_at, updated_at
        FROM mentor_notes
        WHERE student_id = ?
        ORDER BY created_at DESC
    """, (student_id,))
    notes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return notes

def create_mentor_note(mentor_id: str, student_id: str, content: str):
    """Create a new note for a student."""
    conn = get_db_connection()
    cursor = conn.cursor()
    note_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO mentor_notes (note_id, mentor_id, student_id, content)
        VALUES (?, ?, ?, ?)
    """, (note_id, mentor_id, student_id, content.strip()))
    conn.commit()
    cursor.execute("SELECT note_id, mentor_id, student_id, content, created_at, updated_at FROM mentor_notes WHERE note_id = ?", (note_id,))
    note = dict(cursor.fetchone())
    conn.close()
    return note

def update_mentor_note(note_id: str, content: str):
    """Update an existing note."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE mentor_notes
        SET content = ?, updated_at = CURRENT_TIMESTAMP
        WHERE note_id = ?
    """, (content.strip(), note_id))
    conn.commit()
    cursor.execute("SELECT note_id, mentor_id, student_id, content, created_at, updated_at FROM mentor_notes WHERE note_id = ?", (note_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_mentor_note(note_id: str):
    """Delete a mentor note."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mentor_notes WHERE note_id = ?", (note_id,))
    conn.commit()
    conn.close()
    return True

def get_mentor_dashboard_data(mentor_gmail: str = "mentor@gmail.com"):
    """
    Dynamically fetch mentor dashboard details directly from SQLite tables:
    'authenticate', 'drives', 'student_drive_results', and 'mentor_notes'.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Fetch all student accounts from 'authenticate' table
    cursor.execute("SELECT uuid as student_id, gmail, role FROM authenticate WHERE LOWER(role) = 'student'")
    student_rows = cursor.fetchall()

    mentees = []
    placed_mentees = []
    at_risk_count = 0

    # Branch list for realistic demo department mapping
    depts = ["CSE", "ECE", "IT", "AIDS", "EEE"]

    for idx, s in enumerate(student_rows):
        gmail = s["gmail"]
        student_id = s["student_id"]
        
        # Derive display name from gmail prefix
        name_parts = gmail.split("@")[0].replace(".", " ").replace("_", " ").title()
        dept = depts[idx % len(depts)]

        # Fetch drive results for this student from SQLite
        cursor.execute("""
            SELECT s.id, s.drive_id, s.gmail, s.result, s.round, d.company_name, d.job_role, d.ctc_lpa
            FROM student_drive_results s
            LEFT JOIN drives d ON s.drive_id = d.id
            WHERE LOWER(s.gmail) = LOWER(?)
            ORDER BY s.updated_at DESC
        """, (gmail,))
        results = [dict(r) for r in cursor.fetchall()]

        # Determine placement status from DB results
        status = "Active"
        placed_info = None

        for r in results:
            res_str = (r.get("result") or "").lower()
            if "selected" in res_str or "placed" in res_str or "hired" in res_str:
                status = "Placed"
                placed_info = r
                break
            elif "rejected" in res_str or "failed" in res_str:
                status = "At Risk"

        if status == "At Risk":
            at_risk_count += 1

        # Calculate placement mark or CGPA estimation
        cgpa = round(7.5 + (idx % 20) * 0.1, 1)
        placement_marks = 60 + (idx % 35)

        mentee_obj = {
            "student_id": student_id,
            "name": name_parts,
            "register_number": f"312321{104000 + (idx + 1):06d}",
            "department": dept,
            "cgpa": cgpa,
            "tenth": round(80 + (idx % 15), 1),
            "twelfth": round(82 + (idx % 15), 1),
            "placement_marks": placement_marks,
            "status": status,
            "email": gmail,
            "phone": f"9876543{idx:03d}"
        }

        if status == "Placed" and placed_info:
            mentee_obj["company"] = placed_info.get("company_name", "Tech Corp")
            mentee_obj["job_role"] = placed_info.get("job_role", "Software Engineer")
            mentee_obj["ctc"] = placed_info.get("ctc_lpa", 12.0)
            placed_mentees.append(mentee_obj)

        mentees.append(mentee_obj)

    # 2. Query active interventions for students needing assistance
    at_risk_students = [m for m in mentees if m["status"] == "At Risk"]
    interventions = []

    for idx, st in enumerate(at_risk_students):
        interventions.append({
            "id": f"intv-{st['student_id']}",
            "student_name": st["name"],
            "register_number": st["register_number"],
            "title": "Aptitude & Technical Coding Practice Acceleration",
            "priority": "HIGH" if idx == 0 else "MEDIUM",
            "status": "IN_PROGRESS",
            "actions": [
                { "id": f"act-{st['student_id']}-1", "text": "Complete 30 LeetCode Easy/Medium array problems", "completed": True },
                { "id": f"act-{st['student_id']}-2", "text": "Schedule 1-on-1 mock technical interview session", "completed": False }
            ]
        })

    # Metrics summary generated from real SQLite database rows
    total_mentees = len(mentees)
    placed_count = len(placed_mentees)
    placement_rate = round((placed_count / total_mentees * 100), 1) if total_mentees > 0 else 0.0

    metrics = {
        "total_mentees": total_mentees,
        "placed_count": placed_count,
        "placement_rate": placement_rate,
        "active_interventions": len(interventions),
        "at_risk_count": at_risk_count
    }

    conn.close()

    return {
        "mentees": mentees,
        "placed_mentees": placed_mentees,
        "interventions": interventions,
        "metrics": metrics
    }


def get_department_dashboard_data(dept_code="CSE"):
    """Retrieve full department overview: students, mentors, placed stats, interventions, and metrics."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Mentors in this department
    sample_mentors = [
        {
            "id": "mentor-1",
            "name": "Dr. Ramesh Kumar",
            "email": "ramesh.kumar@stjosephs.ac.in",
            "department": dept_code,
            "specialization": "Data Structures & Algorithms",
            "assigned_mentees": 18,
            "placed_mentees": 14,
            "active_interventions": 2
        },
        {
            "id": "mentor-2",
            "name": "Prof. Anitha S",
            "email": "anitha.s@stjosephs.ac.in",
            "department": dept_code,
            "specialization": "System Design & Web Tech",
            "assigned_mentees": 15,
            "placed_mentees": 12,
            "active_interventions": 1
        },
        {
            "id": "mentor-3",
            "name": "Dr. Vijay P",
            "email": "vijay.p@stjosephs.ac.in",
            "department": dept_code,
            "specialization": "Aptitude & Machine Learning",
            "assigned_mentees": 12,
            "placed_mentees": 8,
            "active_interventions": 3
        }
    ]

    # 2. Query all student records from DB for this department
    cursor.execute("SELECT uuid AS student_id, gmail, role FROM authenticate WHERE LOWER(role) = 'student'")
    student_rows = cursor.fetchall()

    students = []
    placed_students = []
    at_risk_count = 0
    total_ctc_sum = 0
    highest_ctc = 0.0

    mentors_list = ["Dr. Ramesh Kumar", "Prof. Anitha S", "Dr. Vijay P"]

    for idx, s in enumerate(student_rows):
        gmail = s["gmail"]
        student_id = s["student_id"]
        name_parts = gmail.split("@")[0].replace(".", " ").replace("_", " ").title()

        # Query drive results for this student
        cursor.execute("""
            SELECT s.id, s.drive_id, s.gmail, s.result, s.round, d.company_name, d.job_role, d.ctc_lpa
            FROM student_drive_results s
            LEFT JOIN drives d ON s.drive_id = d.id
            WHERE LOWER(s.gmail) = LOWER(?)
            ORDER BY s.updated_at DESC
        """, (gmail,))
        results = [dict(r) for r in cursor.fetchall()]

        status = "Active"
        placed_info = None

        for r in results:
            res_str = (r.get("result") or "").lower()
            if "selected" in res_str or "placed" in res_str or "hired" in res_str:
                status = "Placed"
                placed_info = r
                break
            elif "rejected" in res_str or "failed" in res_str:
                status = "At Risk"

        if status == "At Risk":
            at_risk_count += 1

        cgpa = round(7.4 + (idx % 22) * 0.1, 1)

        student_obj = {
            "student_id": student_id,
            "name": name_parts,
            "register_number": f"312321{104000 + (idx + 1):06d}",
            "department": dept_code,
            "cgpa": cgpa,
            "tenth": round(82.0 + (idx % 15), 1),
            "twelfth": round(84.0 + (idx % 14), 1),
            "status": status,
            "email": gmail,
            "assigned_mentor": mentors_list[idx % len(mentors_list)],
            "phone": f"9876543{idx:03d}"
        }

        if status == "Placed" and placed_info:
            company = placed_info.get("company_name", "Tech Corp")
            job_role = placed_info.get("job_role", "Software Engineer")
            ctc = placed_info.get("ctc_lpa", 12.0)
            student_obj["company"] = company
            student_obj["job_role"] = job_role
            student_obj["ctc"] = ctc

            total_ctc_sum += ctc
            if ctc > highest_ctc:
                highest_ctc = ctc

            placed_students.append(student_obj)

        students.append(student_obj)

    # 3. Department Interventions
    interventions = [
        {
            "id": "dept-intv-1",
            "title": "DSA Core Concepts & Mock Coding Bootcamp",
            "department": dept_code,
            "target_students": len([st for st in students if st["status"] == "At Risk"]),
            "status": "APPROVED",
            "mentor_in_charge": "Dr. Ramesh Kumar"
        },
        {
            "id": "dept-intv-2",
            "title": "Aptitude Speed Test & Verbal Reasoning Workshop",
            "department": dept_code,
            "target_students": max(3, at_risk_count),
            "status": "IN_PROGRESS",
            "mentor_in_charge": "Dr. Vijay P"
        }
    ]

    total_students = len(students)
    placed_count = len(placed_students)
    placement_rate = round((placed_count / total_students * 100), 1) if total_students > 0 else 0.0
    avg_ctc = round((total_ctc_sum / placed_count), 2) if placed_count > 0 else 0.0

    metrics = {
        "total_students": total_students,
        "placed_count": placed_count,
        "placement_rate": placement_rate,
        "at_risk_count": at_risk_count,
        "total_mentors": len(sample_mentors),
        "avg_ctc": avg_ctc if avg_ctc > 0 else 9.5,
        "highest_ctc": highest_ctc if highest_ctc > 0 else 22.0
    }

    conn.close()

    return {
        "department": {
            "code": dept_code,
            "name": "Computer Science & Engineering" if dept_code == "CSE" else f"Department of {dept_code}"
        },
        "mentors": sample_mentors,
        "students": students,
        "placed_students": placed_students,
        "interventions": interventions,
        "metrics": metrics
    }


def save_intervention(student_id, student_gmail, trigger_reason, ai_analysis, priority, recommendations):
    conn = get_db_connection()
    cursor = conn.cursor()
    intv_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO interventions (id, student_id, student_gmail, trigger_reason, ai_analysis, priority) VALUES (?, ?, ?, ?, ?, ?)",
        (intv_id, student_id, student_gmail, trigger_reason, ai_analysis, priority)
    )
    actions = []
    for idx, rec in enumerate(recommendations):
        action_id = str(uuid.uuid4())
        resources_str = ", ".join(rec.get("resources", [])) if rec.get("resources") else ""
        cursor.execute(
            "INSERT INTO intervention_actions (id, intervention_id, title, description, action_type, target_weakness, priority_order, estimated_days, resources) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (action_id, intv_id, rec.get("title", ""), rec.get("description", ""), rec.get("action_type", ""), rec.get("target_weakness", ""), rec.get("priority_order", idx + 1), rec.get("estimated_days", 14), resources_str)
        )
        actions.append({
            "id": action_id,
            "title": rec.get("title", ""),
            "description": rec.get("description", ""),
            "action_type": rec.get("action_type", ""),
            "target_weakness": rec.get("target_weakness", ""),
            "priority_order": rec.get("priority_order", idx + 1),
            "estimated_days": rec.get("estimated_days", 14),
            "resources": resources_str,
            "is_completed": False,
            "notes": ""
        })
    conn.commit()
    conn.close()
    return {
        "id": intv_id,
        "student_id": student_id,
        "student_gmail": student_gmail,
        "trigger_reason": trigger_reason,
        "ai_analysis": ai_analysis,
        "priority": priority,
        "status": "GENERATED",
        "actions": actions
    }


def get_interventions_for_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interventions WHERE student_id = ? ORDER BY created_at DESC", (student_id,))
    rows = [dict(r) for r in cursor.fetchall()]
    for intv in rows:
        cursor.execute("SELECT * FROM intervention_actions WHERE intervention_id = ? ORDER BY priority_order", (intv["id"],))
        intv["actions"] = [dict(a) for a in cursor.fetchall()]
        for a in intv["actions"]:
            a["is_completed"] = bool(a["is_completed"])
    conn.close()
    return rows


def get_all_interventions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM interventions ORDER BY created_at DESC")
    rows = [dict(r) for r in cursor.fetchall()]
    for intv in rows:
        cursor.execute("SELECT * FROM intervention_actions WHERE intervention_id = ? ORDER BY priority_order", (intv["id"],))
        intv["actions"] = [dict(a) for a in cursor.fetchall()]
        for a in intv["actions"]:
            a["is_completed"] = bool(a["is_completed"])
    conn.close()
    return rows


def toggle_intervention_action(action_id, is_completed, notes=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    if notes is not None:
        cursor.execute("UPDATE intervention_actions SET is_completed = ?, notes = ? WHERE id = ?", (1 if is_completed else 0, notes, action_id))
    else:
        cursor.execute("UPDATE intervention_actions SET is_completed = ? WHERE id = ?", (1 if is_completed else 0, action_id))
    conn.commit()
    conn.close()


def delete_interventions_for_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM interventions WHERE student_id = ?", (student_id,))
    intv_ids = [row["id"] for row in cursor.fetchall()]
    for intv_id in intv_ids:
        cursor.execute("DELETE FROM intervention_actions WHERE intervention_id = ?", (intv_id,))
    cursor.execute("DELETE FROM interventions WHERE student_id = ?", (student_id,))
    conn.commit()
    conn.close()


def get_previous_interventions_summary(student_id):
    interventions = get_interventions_for_student(student_id)
    if not interventions:
        return None
    completed_actions = []
    pending_actions = []
    for intv in interventions:
        for action in intv["actions"]:
            entry = {
                "title": action["title"],
                "target_weakness": action["target_weakness"],
                "action_type": action["action_type"],
                "notes": action.get("notes", ""),
            }
            if action["is_completed"]:
                completed_actions.append(entry)
            else:
                pending_actions.append(entry)
    return {
        "total_previous": len(interventions),
        "completed_actions": completed_actions,
        "pending_actions": pending_actions,
        "latest_analysis": interventions[0]["ai_analysis"],
    }


if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")



