# Placement Portal - Dedicated Bulk Upload Engine

A complete, self-contained backend microservice for **Excel (`.xlsx` / `.xls`) and CSV Ingestion** with downloadable sample templates, in-memory zero-disk streaming, fuzzy header matching, atomic database upserts, and complete audit logging.

---

## 1. Directory Structure

```text
bulk_upload_module/
├── app.py                      # Standalone FastAPI backend with upload, export, and download routes
├── config.py                   # Storage paths, allowed extensions, and file size limits
├── database.py                 # SQLite data-access layer, schema init, queries, atomic upserts
├── parser.py                   # In-memory streaming, openpyxl / csv parsing, fuzzy header detection
├── exporter.py                 # Styled Excel (.xlsx) and CSV (.csv) data generation & streaming
├── requirements.txt            # Python dependencies (fastapi, uvicorn, openpyxl, etc.)
├── templates_generator.py      # Script generating sample .xlsx and .csv files with formatting
│
├── templates/                  # Ready-to-use sample templates (both Excel and CSV)
│   ├── sample_drive_shortlist.xlsx    # Shortlist mode (emails only)
│   ├── sample_drive_shortlist.csv
│   ├── sample_drive_results.xlsx      # Verdict mode (emails + status + score)
│   ├── sample_drive_results.csv
│   ├── sample_user_access.xlsx        # User accounts & roles roster
│   ├── sample_user_access.csv
│   ├── sample_student_roster.xlsx     # Student academic profiles (CGPA, 10th/12th, skills)
│   ├── sample_student_roster.csv
│   ├── sample_company_drives.xlsx     # Company placement drives scheduling
│   └── sample_company_drives.csv
│
└── tests/
    └── test_bulk_upload.py     # 13 comprehensive integration tests (import, export, templates)
```

---

## 2. Ingestion (Import) Workflows

### 1. Company Placement Drives Scheduling (Import)
- **Endpoint**: `POST /api/upload/company-drives`
- **Files**: `.xlsx`, `.xls`, `.csv`
- **Behavior**: Bulk schedules on-campus and virtual placement drives for visiting companies.
  - Captures `Company Name`, `Job Role`, `CTC LPA`, `Company Type` (`Product`, `Service`, `Consulting`, `Startup`), `Required CGPA`, `Allowed Branches`, `Total Rounds`, `Location`, `Drive Date`, and `Status`.

### 2. Drive Shortlist Upload (Shortlist Mode - Import)
- **Endpoint**: `POST /api/upload/drive-shortlist/{drive_id}`
- **Files**: `.xlsx`, `.xls`, `.csv`
- **Behavior**: Recruiter sends a list of candidate emails who cleared the previous round. The system:
  1. Detects that no `result` column exists.
  2. Increments each student's round index by $+1$ (e.g. Round 1 $\rightarrow$ Round 2).
  3. Updates status to `"Shortlisted for Round N"`.
  4. Executes atomic `INSERT ... ON CONFLICT(drive_id, gmail) DO UPDATE`.

### 3. Drive Results / Verdicts Upload (Verdict Mode - Import)
- **Endpoint**: `POST /api/upload/drive-results/{drive_id}`
- **Files**: `.xlsx`, `.xls`, `.csv`
- **Behavior**: Recruiter sends candidates with explicit evaluation outcomes:
  - Supports statuses: `"Selected"`, `"Rejected"`, `"Shortlisted for Round 3"`, `"On Hold"`.
  - Captures optional test `score` and explicit `round` number.

### 4. Student Academic Profiles Roster (Import)
- **Endpoint**: `POST /api/upload/student-roster`
- **Files**: `.xlsx`, `.xls`, `.csv`
- **Behavior**: Ingests complete student records including `register_number`, `name`, `email`, `department`, `cgpa`, `tenth_percentage`, `twelfth_percentage`, and comma-separated `skills`.
  - Used for pre-placement drive eligibility filtering.

### 5. User Accounts & Role Provisioning (Import)
- **Endpoint**: `POST /api/upload/user-access`
- **Files**: `.xlsx`, `.xls`, `.csv`
- **Behavior**: Onboards batches of users with roles (`Student`, `Mentor`, `Coordinator`, `Recruiter`, `Department`).
  - Automatically provisions fallback passwords (e.g., `student123`, `mentor123`) if password column is empty, or sets custom passwords if provided.
  - Updates existing accounts without collision.

---

## 3. Data Export Workflows (Excel & CSV Download)

All export endpoints support both styled Excel (`.xlsx`) and Excel-compatible UTF-8 CSV (`.csv`) via the query parameter `?format=xlsx` or `?format=csv`.

### 1. Export Company Drives
- **Endpoint**: `GET /api/export/company-drives?format=xlsx` (or `?format=csv`)
- **Output**: Returns full company drive scheduling records (`Company Name`, `Job Role`, `CTC LPA`, `Company Type`, `Required CGPA`, `Allowed Branches`, `Total Rounds`, `Location`, `Drive Date`, `Status`).

### 2. Export Student Drive Results
- **Endpoint**: `GET /api/export/drive-results/{drive_id}?format=xlsx` (or `?format=csv`)
- **Output**: Returns all evaluated student candidates for the specific drive (`Student Gmail`, `Current Round`, `Score / Marks`, `Selection Verdict / Status`, `Last Updated`).

### 3. Export Student Academic Roster
- **Endpoint**: `GET /api/export/student-roster?format=xlsx` (or `?format=csv`)
- **Output**: Returns all registered student academic profiles (`Register Number`, `Full Name`, `Student Email`, `Department`, `CGPA`, `10th%`, `12th%`, `Technical Skills`).

### 4. Export User Access Accounts
- **Endpoint**: `GET /api/export/user-access?format=xlsx` (or `?format=csv`)
- **Output**: Returns active system user credentials and role assignments (`User Email`, `Role`, `Is Active`, `Account Created At`).

---

## 4. Sample Templates Included in `templates/`

| Template File | Primary Columns | Purpose |
| :--- | :--- | :--- |
| `sample_company_drives.xlsx` / `.csv` | `Company Name`, `Job Role`, `CTC LPA`, `Company Type`, `Required CGPA`, `Allowed Branches`, `Rounds`, `Location`, `Date` | Company placement drive scheduling |
| `sample_drive_shortlist.xlsx` / `.csv` | `Student Gmail`, `Student Name`, `Branch` | Recruiter shortlist — auto-increments round |
| `sample_drive_results.xlsx` / `.csv` | `Student Gmail`, `Round`, `Score`, `Result Status` | Final drive outcomes & evaluation scores |
| `sample_student_roster.xlsx` / `.csv` | `Register Number`, `Full Name`, `Student Email`, `Department`, `CGPA`, `10th%`, `12th%`, `Skills` | Student academic profile master data |
| `sample_user_access.xlsx` / `.csv` | `User Email`, `Role`, `Password` | Bulk user accounts & role onboarding |

---

## 5. How to Run the Backend

```powershell
# 1. Navigate to the bulk upload module folder
cd bulk_upload_module

# 2. (Optional) Re-generate templates
python templates_generator.py

# 3. Start the FastAPI server
python app.py
```

The server will start at:
- **API URL**: `http://127.0.0.1:8001`
- **Interactive Swagger Docs**: `http://127.0.0.1:8001/docs`

---

## 6. Complete API Endpoints Reference

### Template Downloads
- `GET /api/templates`: Lists all available templates with required and optional headers.
- `GET /api/templates/download/{filename}`: Downloads a sample `.xlsx` or `.csv` file.

### Ingestion (Import) Endpoints
- `POST /api/upload/company-drives` (Form-data: `file`)
- `POST /api/upload/drive-shortlist/{drive_id}` (Form-data: `file`)
- `POST /api/upload/drive-results/{drive_id}` (Form-data: `file`)
- `POST /api/upload/student-roster` (Form-data: `file`)
- `POST /api/upload/user-access` (Form-data: `file`, `default_role`)

### Export Endpoints
- `GET /api/export/company-drives?format=xlsx|csv`: Export all company drives.
- `GET /api/export/drive-results/{drive_id}?format=xlsx|csv`: Export candidate results for a drive.
- `GET /api/export/student-roster?format=xlsx|csv`: Export student roster.
- `GET /api/export/user-access?format=xlsx|csv`: Export user accounts.

### Verification & Query Endpoints
- `GET /api/drives`: View all placement drives.
- `GET /api/drives/{drive_id}/results`: View candidate results for a drive.
- `GET /api/users`: View all onboarded user accounts.
- `GET /api/students`: View all student profiles in roster.
- `GET /api/logs`: View audit logs of all upload jobs.

---

## 7. Running Automated Tests

Run the included Pytest suite to verify all ingestion and export flows:
```powershell
python -m pytest tests/test_bulk_upload.py -v
```
All 13 tests verify:
- Health check & API root metadata
- Template downloads (`.xlsx` & `.csv`)
- Company drives bulk upload (Excel & CSV)
- Shortlist round auto-promotion (Excel)
- Verdict and score persistence (CSV)
- User role upsertion (Excel)
- Student profile parsing (Excel)
- Empty file & missing column error handling
- Company drives export (`.xlsx` & `.csv`)
- Drive candidate results export (`.xlsx` & `.csv`)
- Student roster export (`.xlsx` & `.csv`)
- User access accounts export (`.xlsx` & `.csv`)
