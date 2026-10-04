# Database Structure & Entity Relationship Flowchart

This document provides a comprehensive visual and textual guide to the database architecture for the **Placement & Interview Performance Tracking System**.

---

## 1. Complete Entity-Relationship (ER) Diagram

The diagram below illustrates all 15 database tables, their primary keys (`PK`), foreign keys (`FK`), unique keys (`UK`), and their cardinalities.

```mermaid
erDiagram
    AUTHENTICATE {
        string gmail PK
        string password
        string user_id
        string role
        boolean is_active
        datetime created_at
    }

    STUDENTS {
        string student_id PK
        string name
        string register_number UK
        string email UK
        string department
        float cgpa
        float tenth_percentage
        float twelfth_percentage
        float placement_marks
        json skills
        string resume_path
        string status_id FK
        datetime created_at
    }

    COORDINATORS {
        string coordinator_id PK
        string name
        string email UK
        string department
    }

    MENTORS {
        string mentor_id PK
        string name
        string email UK
        string department
        string specialization
        int max_mentees
        int current_mentee_count
    }

    STATUS {
        string status_id PK
        json failed_attempts
        json successful_attempts
    }

    STUDENT_ACCESS {
        string access_id PK
        string student_id FK,UK
        string coordinator_id FK
        enum status
        datetime invitation_sent_at
        datetime activated_at
        datetime last_login_at
        datetime revoked_at
        datetime created_at
        datetime updated_at
    }

    ACCESS_HISTORY {
        string id PK
        string student_access_id FK
        string action
        string actor
        datetime timestamp
    }

    DRIVES {
        string drive_id PK
        string company_name
        enum company_type
        string role_title
        float package_lpa
        date drive_date
        float required_cgpa
        float required_tenth
        float required_twelfth
        int total_rounds
        enum drive_status
        string coordinator_id FK
        datetime created_at
    }

    ROUNDS {
        string round_id PK
        string drive_id FK
        enum round_type
        int round_number
        string round_name
        string description
        int total_appeared
        int total_passed
    }

    ROUND_RESULTS {
        string result_id PK
        string student_id FK
        string round_id FK
        string drive_id FK
        enum result
        float score
        float max_score
        string rejection_reason
        string feedback
        string weakness_area
        date attempt_date
    }

    STUDENT_DRIVE_REGISTRATIONS {
        string registration_id PK
        string student_id FK
        string drive_id FK
        string final_status
        int rounds_cleared
        datetime registered_at
    }

    MENTOR_STUDENTS {
        string id PK
        string mentor_id FK
        string student_id FK
        datetime assigned_at
    }

    MENTOR_NOTES {
        string note_id PK
        string mentor_id FK
        string student_id FK
        string content
        datetime created_at
        datetime updated_at
    }

    INTERVENTIONS {
        string intervention_id PK
        string student_id FK
        string coordinator_id FK
        string mentor_id FK
        string trigger_reason
        json failure_summary
        string ai_analysis
        json recommendations
        enum priority
        enum status
        datetime created_at
        datetime updated_at
        datetime approved_at
        datetime completed_at
    }

    INTERVENTION_ACTIONS {
        string action_id PK
        string intervention_id FK
        string action_type
        string title
        string description
        string target_weakness
        json resources
        string assigned_to FK
        boolean is_completed
        date due_date
        datetime completed_at
        string notes
        datetime created_at
    }

    %% Relationships
    STUDENTS }|--o| STATUS : "has status (1:1)"
    STUDENTS ||--o| STUDENT_ACCESS : "has access record (1:1)"
    COORDINATORS ||--o{ STUDENT_ACCESS : "manages access (1:N)"
    STUDENT_ACCESS ||--o{ ACCESS_HISTORY : "tracks access events (1:N)"
    
    COORDINATORS ||--o{ DRIVES : "manages placement drive (1:N)"
    DRIVES ||--o{ ROUNDS : "contains selection rounds (1:N)"
    DRIVES ||--o{ STUDENT_DRIVE_REGISTRATIONS : "has drive registrations (1:N)"
    STUDENTS ||--o{ STUDENT_DRIVE_REGISTRATIONS : "registers for drives (1:N)"
    
    ROUNDS ||--o{ ROUND_RESULTS : "records student scores (1:N)"
    STUDENTS ||--o{ ROUND_RESULTS : "participates in rounds (1:N)"
    DRIVES ||--o{ ROUND_RESULTS : "tracks overall results (1:N)"

    MENTORS ||--o{ MENTOR_STUDENTS : "mentors students (1:N)"
    STUDENTS ||--o{ MENTOR_STUDENTS : "assigned to mentors (1:N)"
    MENTORS ||--o{ MENTOR_NOTES : "writes notes for (1:N)"
    STUDENTS ||--o{ MENTOR_NOTES : "receives notes (1:N)"

    STUDENTS ||--o{ INTERVENTIONS : "targeted by intervention (1:N)"
    COORDINATORS ||--o{ INTERVENTIONS : "initiates/approves intervention (1:N)"
    MENTORS ||--o| INTERVENTIONS : "assigned to oversee intervention (0..1:N)"
    INTERVENTIONS ||--o{ INTERVENTION_ACTIONS : "prescribes actions (1:N)"
    MENTORS ||--o| INTERVENTION_ACTIONS : "assigned action item (0..1:N)"
```

---

## 2. Module Breakdown Flowcharts

### Module A: User Identity & Access Management Flowchart

This subsystem handles role-based credentials (`AUTHENTICATE`), student profiles (`STUDENTS`), coordinator profiles (`COORDINATORS`), and invitation/access history (`STUDENT_ACCESS`, `ACCESS_HISTORY`).

```mermaid
flowchart TD
    subgraph AuthSystem ["Authentication & Access System"]
        A[AUTHENTICATE<br/><i>gmail, password, role, user_id</i>]
    end

    subgraph UserEntities ["User Profiles"]
        S[STUDENTS<br/><i>student_id, register_number, email...</i>]
        C[COORDINATORS<br/><i>coordinator_id, name, email...</i>]
        M[MENTORS<br/><i>mentor_id, name, email...</i>]
    end

    subgraph StatusAndAccess ["Access Tracking & Status"]
        ST[STATUS<br/><i>status_id, failed_attempts, successful_attempts</i>]
        SA[STUDENT_ACCESS<br/><i>access_id, student_id, status, timestamps</i>]
        AH[ACCESS_HISTORY<br/><i>id, student_access_id, action, actor</i>]
    end

    A -->|Polymorphic user_id by role| S
    A -->|Polymorphic user_id by role| C
    A -->|Polymorphic user_id by role| M

    S -->|status_id FK| ST
    S -->|1:1 FK in student_access| SA
    C -->|coordinator_id FK| SA
    SA -->|1:N student_access_id FK| AH

    style AuthSystem fill:#1e1e2e,stroke:#89b4fa,color:#cdd6f4
    style UserEntities fill:#1e1e2e,stroke:#a6e3a1,color:#cdd6f4
    style StatusAndAccess fill:#1e1e2e,stroke:#f9e2af,color:#cdd6f4
```

---

### Module B: Placement Drives & Round Evaluation Flowchart

This subsystem tracks placement companies (`DRIVES`), interview rounds (`ROUNDS`), student registrations (`STUDENT_DRIVE_REGISTRATIONS`), and individual round outcomes (`ROUND_RESULTS`).

```mermaid
flowchart TD
    C[COORDINATORS<br/><i>coordinator_id</i>] -->|1:N Manages| D[DRIVES<br/><i>drive_id, company_name, package_lpa, status</i>]
    
    D -->|1:N Contains| R[ROUNDS<br/><i>round_id, round_type, round_number</i>]
    D -->|1:N Has Registrations| SDR[STUDENT_DRIVE_REGISTRATIONS<br/><i>registration_id, final_status, rounds_cleared</i>]
    
    S[STUDENTS<br/><i>student_id</i>] -->|1:N Registers for| SDR
    S -->|1:N Attempts| RR[ROUND_RESULTS<br/><i>result_id, score, result, weakness_area</i>]
    
    R -->|1:N Generates| RR
    D -->|1:N Tracks| RR

    style D fill:#2d1b69,stroke:#b4befe,color:#cdd6f4
    style R fill:#2d1b69,stroke:#b4befe,color:#cdd6f4
    style SDR fill:#2d1b69,stroke:#b4befe,color:#cdd6f4
    style RR fill:#2d1b69,stroke:#f38ba8,color:#cdd6f4
```

---

### Module C: Mentorship System Flowchart

Connects students with assigned mentors (`MENTOR_STUDENTS`) and allows mentors to log performance feedback (`MENTOR_NOTES`).

```mermaid
flowchart TD
    M[MENTORS<br/><i>mentor_id, max_mentees, current_mentee_count</i>]
    S[STUDENTS<br/><i>student_id, name, register_number</i>]
    
    MS[MENTOR_STUDENTS<br/><i>Junction Table: id, mentor_id, student_id</i>]
    MN[MENTOR_NOTES<br/><i>note_id, mentor_id, student_id, content</i>]

    M -->|1:N Assigns| MS
    S -->|1:N Assigned to| MS
    
    M -->|1:N Writes| MN
    S -->|1:N Subject of| MN

    style M fill:#181825,stroke:#fab387,color:#cdd6f4
    style S fill:#181825,stroke:#a6e3a1,color:#cdd6f4
    style MS fill:#313244,stroke:#cba6f7,color:#cdd6f4
    style MN fill:#313244,stroke:#cba6f7,color:#cdd6f4
```

---

### Module D: AI Interventions & Remedial Action Flowchart

When students perform poorly in recruitment drives, the system triggers an AI intervention (`INTERVENTIONS`), reviewed by coordinators/mentors, which creates actionable task items (`INTERVENTION_ACTIONS`).

```mermaid
flowchart TD
    S[STUDENTS<br/><i>student_id</i>] -->|1:N Target of| I[INTERVENTIONS<br/><i>intervention_id, trigger_reason, ai_analysis, priority, status</i>]
    C[COORDINATORS<br/><i>coordinator_id</i>] -->|1:N Initiates/Approves| I
    M[MENTORS<br/><i>mentor_id</i>] -.->|0..1:N Assigned to| I

    I -->|1:N Prescribes| IA[INTERVENTION_ACTIONS<br/><i>action_id, title, description, target_weakness, due_date</i>]
    M -.->|0..1:N Assigned Action| IA

    style I fill:#3b0764,stroke:#f5c2e7,color:#cdd6f4
    style IA fill:#3b0764,stroke:#f5c2e7,color:#cdd6f4
```

---

## 3. Data Flow & Inter-System Workflow

The flowchart below traces data movement across all system workflows: student registration -> drive execution -> round scoring -> AI intervention trigger -> mentor intervention action execution.

```mermaid
flowchart LR
    subgraph Step1 ["1. Onboarding & Access"]
        direction TB
        Coord[Coordinator] -->|Invites Student| SA[StudentAccess]
        SA -->|Activated| Auth[Authenticate]
    end

    subgraph Step2 ["2. Drive Creation & Registration"]
        direction TB
        Coord -->|Creates Drive| Drive[Drives]
        Drive -->|Defines Rounds| Round[Rounds]
        Stud[Student] -->|Registers| Reg[StudentDriveRegistrations]
    end

    subgraph Step3 ["3. Drive Execution & Scoring"]
        direction TB
        Stud -->|Appears in Round| RR[RoundResult]
        RR -->|Calculates Cleared Rounds| Reg
    end

    subgraph Step4 ["4. AI Intervention & Remediation"]
        direction TB
        RR -->|If FAILED / Weakness Identified| AI[AI Analysis Engine]
        AI -->|Generates| Interv[Interventions]
        Coord -->|Approves| Interv
        Interv -->|Creates Action Items| Act[InterventionActions]
        Act -->|Assigned to| Mentor[Mentor]
        Mentor -->|Log Guidance| Notes[MentorNotes]
    end

    Step1 --> Step2 --> Step3 --> Step4
```

---

## 4. Comprehensive Schema Dictionary

| Table Name | Primary Key | Foreign Keys | Key Columns | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **`students`** | `student_id` | `status_id` -> `status.status_id` | `register_number`, `email`, `cgpa`, `tenth_percentage`, `twelfth_percentage`, `skills` | Stores core academic & contact profile for placement candidates. |
| **`coordinators`** | `coordinator_id` | None | `name`, `email`, `department` | Placement officer / department coordinator accounts. |
| **`mentors`** | `mentor_id` | None | `name`, `email`, `specialization`, `max_mentees`, `current_mentee_count` | Faculty / industry mentors assisting low-performing students. |
| **`status`** | `status_id` | None | `failed_attempts` (JSON), `successful_attempts` (JSON) | Summarizes student interview outcomes and history aggregations. |
| **`student_access`** | `access_id` | `student_id` -> `students.student_id`, `coordinator_id` -> `coordinators.coordinator_id` | `status` (`NO_ACCESS`, `INVITED`, `ACTIVE`, `REVOKED`), `invitation_sent_at`, `activated_at` | Controls portal access permissions for students. |
| **`access_history`** | `id` | `student_access_id` -> `student_access.access_id` | `action`, `actor`, `timestamp` | Audit log of access state changes (invitations, activations, revocations). |
| **`drives`** | `drive_id` | `coordinator_id` -> `coordinators.coordinator_id` | `company_name`, `company_type`, `package_lpa`, `required_cgpa`, `drive_status` | Recruitment drive hosted by hiring companies. |
| **`rounds`** | `round_id` | `drive_id` -> `drives.drive_id` | `round_type`, `round_number`, `round_name`, `total_appeared`, `total_passed` | Individual selection stage within a placement drive. |
| **`round_results`** | `result_id` | `student_id` -> `students.student_id`, `round_id` -> `rounds.round_id`, `drive_id` -> `drives.drive_id` | `result` (`PASSED`, `FAILED`), `score`, `weakness_area`, `feedback` | Outcome of a specific student in a specific drive round. |
| **`student_drive_registrations`** | `registration_id` | `student_id` -> `students.student_id`, `drive_id` -> `drives.drive_id` | `final_status`, `rounds_cleared`, `registered_at` | Student enrollment record for a company drive. |
| **`mentor_students`** | `id` | `mentor_id` -> `mentors.mentor_id`, `student_id` -> `students.student_id` | `assigned_at` | Junction table mapping mentor-to-student assignments. |
| **`mentor_notes`** | `note_id` | `mentor_id` -> `mentors.mentor_id`, `student_id` -> `students.student_id` | `content`, `created_at`, `updated_at` | Qualitative feedback and interaction notes written by mentors. |
| **`interventions`** | `intervention_id` | `student_id` -> `students.student_id`, `coordinator_id` -> `coordinators.coordinator_id`, `mentor_id` -> `mentors.mentor_id` | `trigger_reason`, `failure_summary`, `ai_analysis`, `priority`, `status` | System or AI generated intervention case for struggling students. |
| **`intervention_actions`** | `action_id` | `intervention_id` -> `interventions.intervention_id`, `assigned_to` -> `mentors.mentor_id` | `title`, `description`, `target_weakness`, `is_completed`, `due_date` | Prescribed remedial tasks assigned to resolve identified skill gaps. |
| **`authenticate`** | `gmail` | `user_id` (Polymorphic FK) | `password`, `user_id`, `role`, `is_active` | Central authentication store for logins across all roles. |

---

## 5. Enumeration Types Reference

| Enum Name | Defined Values | Usage Location |
| :--- | :--- | :--- |
| **`CompanyType`** | `PRODUCT`, `SERVICE`, `STARTUP`, `CONSULTING` | `drives.company_type` |
| **`DriveStatus`** | `UPCOMING`, `ONGOING`, `COMPLETED`, `CANCELLED` | `drives.drive_status` |
| **`RoundType`** | `APTITUDE`, `CODING`, `TECHNICAL`, `MANAGERIAL`, `HR`, `GROUP_DISCUSSION` | `rounds.round_type` |
| **`Result`** | `PASSED`, `FAILED` | `round_results.result` |
| **`Priority`** | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | `interventions.priority` |
| **`InterventionStatus`** | `GENERATED`, `PENDING_REVIEW`, `APPROVED`, `IN_PROGRESS`, `COMPLETED`, `DISMISSED` | `interventions.status` |
| **`AccessStatus`** | `NO_ACCESS`, `INVITED`, `ACTIVE`, `REVOKED` | `student_access.status` |

---

## 6. Relationship Summary & Cardinality Rules

1. **Student to Status (`1 : 0..1`)**: A student may reference a `status` record containing aggregated success/failure history.
2. **Student to StudentAccess (`1 : 1`)**: Each student has exactly one access record enforcing portal permission state.
3. **Student to RoundResults (`1 : N`)**: A student can participate in multiple drive rounds, producing multiple `round_results`.
4. **Drive to Rounds (`1 : N`)**: Each placement drive contains one or more ordered recruitment `rounds`.
5. **Drive to StudentDriveRegistrations (`1 : N`)**: Multiple students register for a single drive.
6. **Mentor to Student (`N : M`)**: Managed via `mentor_students` junction table, mapping mentors to assigned mentees.
7. **Intervention to InterventionAction (`1 : N`)**: An intervention case breaks down into multiple prescribed action items.
