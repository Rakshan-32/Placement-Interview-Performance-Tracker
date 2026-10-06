import db


def list_drives():
    drives = db.get_all_drives()
    for drive in drives:
        drive["results_count"] = db.get_drive_results_count(drive["id"])
    return drives


def create_drive(data):
    return db.create_drive(
        company_name=data.company_name.strip(),
        job_role=data.job_role.strip(),
        ctc_lpa=data.ctc_lpa,
        min_cgpa=data.min_cgpa,
        allowed_branches=data.allowed_branches.strip(),
        location=data.location.strip(),
        status=data.status.strip() if data.status else "Active",
        deadline=data.deadline,
    )


def get_results(drive_id):
    return db.get_drive_results(drive_id)


def get_drive(drive_id):
    return db.get_drive(drive_id)
